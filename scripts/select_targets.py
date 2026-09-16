"""Decide which configured repositories a single publish run reaches.

One filter, used in two places: `publish.py` to choose what to sync, and the sync workflow to
scope the App token. They must agree -- a run that syncs two repositories while holding a token
for twenty is the defect this exists to prevent.

Two failure modes are deliberately loud:

* **An unmatched or disabled name aborts** before anything is cloned. Silently narrowing a
  fleet-wide run because of a typo is worse than refusing to run.
* **An empty selection is never emitted.** `actions/create-github-app-token` documents that
  "if `owner` is set and `repositories` is empty, access will be scoped to all repositories in
  the provided repository owner's installation" -- so an empty value does not narrow the token,
  it maximises it.

Scoping only ever narrows. `enabled` in `config/targets.json` remains the outer gate: a target
that is not enabled cannot be reached by naming it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

SEPARATORS = (",", "\n")


class SelectionError(RuntimeError):
    """Raised when a run's scope cannot be resolved safely."""


def parse_requested(raw: str | None) -> list[str] | None:
    """Split the operator's input. None means "every enabled target"."""
    if raw is None or not raw.strip():
        return None

    normalised = raw
    for separator in SEPARATORS:
        normalised = normalised.replace(separator, ",")
    requested = [part.strip() for part in normalised.split(",") if part.strip()]
    if not requested:
        # The operator typed something -- a stray comma, say -- so this is a typo rather than a
        # request for the whole fleet. Falling through to "everything" here would turn a
        # keystroke into a fleet-wide run.
        raise SelectionError(f"Requested targets named no repository: {raw!r}")
    return requested


def _enabled_targets(config: dict[str, Any]) -> list[dict[str, Any]]:
    raw_targets = config.get("targets")
    if not isinstance(raw_targets, list):
        raise SelectionError("config must contain a 'targets' array.")
    return [
        target
        for target in raw_targets
        if isinstance(target, dict)
        and isinstance(target.get("repo"), str)
        and target.get("enabled", True)
    ]


def _matches(target_repo: str, requested: str) -> bool:
    """Exact match on the full `owner/name`, or on the name alone. Never a prefix.

    A prefix match would let `python` select `python-course`, quietly writing to a repository
    the operator deliberately excluded.
    """
    owner_and_name = target_repo.casefold()
    name = owner_and_name.split("/", 1)[1]
    wanted = requested.casefold()
    return wanted == owner_and_name or wanted == name


def select_targets(config: dict[str, Any], requested: list[str] | None) -> list[dict[str, Any]]:
    """Resolve a run's targets, raising rather than returning an empty or surprising set."""
    enabled = _enabled_targets(config)
    if not enabled:
        raise SelectionError("config has no enabled targets; refusing to resolve an empty scope.")

    if requested is None:
        return enabled

    all_targets = [t for t in config.get("targets", []) if isinstance(t, dict) and isinstance(t.get("repo"), str)]
    selected: list[dict[str, Any]] = []
    for wanted in requested:
        matches = [target for target in enabled if _matches(target["repo"], wanted)]
        if len(matches) > 1:
            names = ", ".join(sorted(target["repo"] for target in matches))
            raise SelectionError(f"Requested target {wanted!r} is ambiguous; it matches {names}.")
        if not matches:
            disabled = [t for t in all_targets if _matches(t["repo"], wanted)]
            if disabled:
                raise SelectionError(
                    f"Requested target {wanted!r} is configured but not enabled. "
                    "Scoping a run narrows it; it cannot reach a disabled target."
                )
            raise SelectionError(f"Requested target {wanted!r} is not in the target configuration.")
        if matches[0] not in selected:
            selected.append(matches[0])

    if not selected:
        raise SelectionError("Requested targets resolved to nothing; refusing to run.")

    # Return configuration order, not the order the operator typed, so a scoped run visits
    # repositories in the same sequence an unscoped one would.
    chosen = {target["repo"] for target in selected}
    return [target for target in enabled if target["repo"] in chosen]


def repository_names(selected: list[dict[str, Any]]) -> list[str]:
    """Bare repository names, the form the token action's `repositories` input takes."""
    if not selected:
        raise SelectionError("Refusing to emit an empty repository list: it widens the token.")
    return [target["repo"].split("/", 1)[1] for target in selected]


def excluded_targets(config: dict[str, Any], selected: list[dict[str, Any]]) -> list[str]:
    """Enabled targets this run is deliberately not touching, so a log can name them."""
    chosen = {target["repo"] for target in selected}
    return [target["repo"] for target in _enabled_targets(config) if target["repo"] not in chosen]


def render_output(config_path: Path, raw_request: str | None) -> str:
    """Build the single `repositories=` line the workflow step writes to its step output."""
    if raw_request and any(character in raw_request for character in ("\n", "\r", "=")):
        # This value is written to a step output file. A newline or an '=' could append a second
        # assignment and silently replace the scope computed here.
        raise SelectionError("Requested targets may not contain a newline or '='.")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    selected = select_targets(config, parse_requested(raw_request))
    return "repositories=" + ",".join(repository_names(selected))


def main() -> int:
    config_path = Path(__file__).resolve().parents[1] / "config" / "targets.json"
    try:
        line = render_output(config_path, os.environ.get("REQUESTED_TARGETS"))
    except (SelectionError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
