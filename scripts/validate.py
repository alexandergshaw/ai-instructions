from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from sync_payload import MANAGED_ROOTS, managed_area_description

REPO_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
FORBIDDEN_FILENAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def validate_repository_name(value: str) -> bool:
    return bool(REPO_NAME_PATTERN.fullmatch(value))


def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_targets_config(config_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = load_json_file(config_path)
    except FileNotFoundError:
        return [f"Missing target configuration file: {config_path}"]
    except json.JSONDecodeError as exc:
        return [f"Failed to parse {config_path}: {exc}"]

    if not isinstance(data, dict):
        return ["config/targets.json must contain a JSON object."]

    targets = data.get("targets")
    if not isinstance(targets, list):
        return ["config/targets.json must contain a 'targets' array."]

    seen_repos: set[str] = set()
    for index, target in enumerate(targets):
        prefix = f"config/targets.json targets[{index}]"
        if not isinstance(target, dict):
            errors.append(f"{prefix} must be an object.")
            continue

        repo = target.get("repo")
        if not isinstance(repo, str) or not validate_repository_name(repo):
            errors.append(f"{prefix}.repo must match owner/repository.")
        elif repo in seen_repos:
            errors.append(f"Duplicate repository entry: {repo}")
        else:
            seen_repos.add(repo)

        enabled = target.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            errors.append(f"{prefix}.enabled must be a boolean when present.")

        profile = target.get("profile")
        if profile is not None and not isinstance(profile, str):
            errors.append(f"{prefix}.profile must be a string when present.")

        languages = target.get("languages")
        if languages is not None and (
            not isinstance(languages, list) or not all(isinstance(language, str) for language in languages)
        ):
            errors.append(f"{prefix}.languages must be an array of strings when present.")

    return errors


def _contains_forbidden_filename(path: Path) -> bool:
    return path.name in FORBIDDEN_FILENAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES


FRONTMATTER_FIELD_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?: (.*))?$")


# A plain (unquoted) YAML scalar may not begin with any of these.
YAML_INDICATORS = set("-?:,[]{}#&*!|>'\"%@`")


def _unquote(value: str) -> tuple[str, bool]:
    """Return the value with its surrounding quotes removed, and whether it was truly quoted.

    A value merely starting and ending with a quote character is not a quoted scalar --
    `"a" and "b"` is not -- so the quote must not recur inside.
    """
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        inner = value[1:-1]
        if value[0] not in inner:
            return inner, True
    return value, False


def validate_skill_frontmatter(skill_dir: Path, payload_root: Path) -> list[str]:
    """A skill is discovered by its frontmatter, so frontmatter no loader can read is inert.

    This deliberately refuses anything it cannot parse unambiguously rather than guessing.
    A validator that accepts frontmatter a YAML loader would reject is worse than no
    validator, because it certifies a skill that will silently fail to load downstream.
    """
    skill_file = skill_dir / "SKILL.md"
    relative = skill_file.relative_to(payload_root).as_posix()
    try:
        lines = skill_file.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError:
        return [f"Skill must be UTF-8 encoded: {relative}"]

    if not lines or lines[0].strip() != "---":
        return [f"Skill must open with YAML frontmatter: {relative}"]

    closing = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if closing is None:
        return [f"Skill frontmatter is not closed by a '---' line: {relative}"]

    errors: list[str] = []
    fields: dict[str, str] = {}
    previous_key_had_value = False
    for line in lines[1:closing]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        if line[:1].isspace():
            # Indented under a key that already had a scalar value, this is a wrapped plain
            # scalar, whose meaning depends on YAML rules this validator does not implement.
            if previous_key_had_value:
                errors.append(
                    f"Skill frontmatter value must be on one line: {relative}: {line.strip()!r}"
                )
            # Otherwise it is a nested block, which belongs to the key above, not the top level.
            continue

        match = FRONTMATTER_FIELD_PATTERN.match(line)
        if match is None:
            errors.append(f"Skill frontmatter line must be 'key: value': {relative}: {line!r}")
            previous_key_had_value = False
            continue

        key, raw_value = match.group(1), (match.group(2) or "").strip()
        previous_key_had_value = bool(raw_value)
        if not raw_value:
            fields[key] = ""
            continue

        value, quoted = _unquote(raw_value)
        if not quoted:
            if raw_value[0] in YAML_INDICATORS:
                errors.append(
                    f"Skill frontmatter value starting with '{raw_value[0]}' must be quoted: "
                    f"{relative}: {key}"
                )
                continue
            if ": " in raw_value or raw_value.endswith(":"):
                errors.append(
                    f"Skill frontmatter value containing a colon must be quoted: {relative}: {key}"
                )
                continue
        fields[key] = value

    name = fields.get("name", "")
    if not name:
        errors.append(f"Skill frontmatter must define a non-empty name: {relative}")
    elif name != skill_dir.name:
        errors.append(f"Skill frontmatter name must match its directory ({skill_dir.name}): {relative}")

    if not fields.get("description"):
        errors.append(f"Skill frontmatter must define a non-empty description: {relative}")

    return errors


def validate_payload(payload_root: Path) -> list[str]:
    errors: list[str] = []
    if not payload_root.is_dir():
        return [f"Missing payload directory: {payload_root}"]

    if (payload_root / "AGENTS.md").exists():
        errors.append("payload/ must not contain a root AGENTS.md file.")

    root_claude = payload_root / "CLAUDE.md"
    if root_claude.exists():
        errors.append("payload/ must not contain a root CLAUDE.md file.")

    if (payload_root / "DEVELOPMENT-LOOP.md").exists():
        errors.append("payload/ must not contain DEVELOPMENT-LOOP.md; it is a control-plane file.")

    if (payload_root / ".claude" / "rules").exists():
        errors.append("payload/ must not contain repository-local .claude/rules content.")

    skills_root = payload_root / ".claude" / "skills"

    for path in sorted(payload_root.rglob("*")):
        try:
            path.resolve().relative_to(payload_root.resolve())
        except ValueError:
            errors.append(f"Payload entry escapes the payload root: {path}")
            continue

        if path.is_symlink():
            errors.append(f"Payload must not contain symlinks: {path}")
            continue

        if _contains_forbidden_filename(path):
            errors.append(f"Forbidden secret-like file detected in payload: {path.relative_to(payload_root)}")

        if path.is_file():
            first_component = path.relative_to(payload_root).parts[0]
            if first_component not in MANAGED_ROOTS:
                errors.append(
                    f"Payload content must live under {managed_area_description()}: "
                    f"{path.relative_to(payload_root).as_posix()}"
                )

        if path.is_file() and path.suffix.lower() == ".md":
            try:
                contents = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                errors.append(f"Markdown file must be UTF-8 encoded: {path.relative_to(payload_root)}")
                continue
            if not contents.strip():
                errors.append(f"Markdown file must be non-empty: {path.relative_to(payload_root)}")

    if skills_root.exists():
        for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
            if not skill_dir.name.startswith("shared-"):
                errors.append(f"Centrally distributed skill directories must begin with 'shared-': {skill_dir.name}")
            if not (skill_dir / "SKILL.md").is_file():
                errors.append(f"Skill directory is missing SKILL.md: {skill_dir.relative_to(payload_root)}")
                continue
            errors.extend(validate_skill_frontmatter(skill_dir, payload_root))

    return errors


def validate_control_plane(repo_root: Path) -> list[str]:
    errors: list[str] = []
    required_files = [
        repo_root / "AGENTS.md",
        repo_root / "CLAUDE.md",
        repo_root / ".github" / "copilot-instructions.md",
    ]

    for path in required_files:
        if not path.is_file():
            errors.append(f"Missing required control-plane file: {path.relative_to(repo_root)}")
            continue
        if not path.read_text(encoding="utf-8").strip():
            errors.append(f"Control-plane file must be non-empty: {path.relative_to(repo_root)}")

    return errors


def validate_repository(repo_root: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(validate_control_plane(repo_root))
    errors.extend(validate_targets_config(repo_root / "config" / "targets.json"))
    errors.extend(validate_payload(repo_root / "payload"))
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    errors = validate_repository(repo_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
