from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

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


def validate_payload(payload_root: Path) -> list[str]:
    errors: list[str] = []
    if not payload_root.is_dir():
        return [f"Missing payload directory: {payload_root}"]

    root_claude = payload_root / "CLAUDE.md"
    if root_claude.exists():
        errors.append("payload/ must not contain a root CLAUDE.md file.")

    shared_root = payload_root / ".claude" / "shared"
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

        if path.is_file() and path.suffix.lower() == ".md":
            if not path.read_text(encoding="utf-8").strip():
                errors.append(f"Markdown file must be non-empty: {path.relative_to(payload_root)}")

    if skills_root.exists():
        for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
            if not skill_dir.name.startswith("shared-"):
                errors.append(f"Centrally distributed skill directories must begin with 'shared-': {skill_dir.name}")
            if not (skill_dir / "SKILL.md").is_file():
                errors.append(f"Skill directory is missing SKILL.md: {skill_dir.relative_to(payload_root)}")

    if shared_root.exists():
        for path in sorted(shared_root.rglob("*.md")):
            if not path.read_text(encoding="utf-8").strip():
                errors.append(f"Shared Markdown file must be non-empty: {path.relative_to(payload_root)}")

    return errors


def validate_repository(repo_root: Path) -> list[str]:
    errors: list[str] = []
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
