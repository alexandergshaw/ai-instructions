from __future__ import annotations

import json
import os
import fnmatch
import shutil
import sys
from pathlib import Path
from typing import Any

MANIFEST_RELATIVE_PATH = Path(".claude/.central-instructions-manifest.json")
MANIFEST_SOURCE = "central-claude-instructions"

# The area this system owns downstream, and therefore the only area it may delete from or write
# into. This is the boundary README documents -- not the whole of `.claude/`, which also holds
# content the downstream repository authored for itself.
#
# The manifest that authorizes deletions lives inside the downstream repository, so it is untrusted
# input: it can be corrupted or hand-edited, and without this bound it could name any path.
#
# A pattern ending in "/" selects a directory and everything beneath it. Any other pattern must
# equal a full path. Matching is per path component, and "*" is allowed within one component --
# so `.claude/skills/shared-*/` covers every distributed skill and no locally authored one.
MANAGED_AREAS = (
    ".claude/shared/",
    ".claude/skills/shared-*/",
    ".claude/.central-instructions-manifest.json",
)

# Every distribution carries these, whatever else a selection excludes. They arrive through
# .claude/skills/, which a downstream repository discovers on its own -- unlike .claude/shared/**,
# which loads only where that repository's own instructions import it. Entries follow the same
# matching rule as a selection prefix: a trailing "/" selects a directory, anything else is an
# exact path.
REQUIRED_PAYLOAD_PATHS = (
    ".claude/skills/shared-agent-floor/",
    ".claude/skills/shared-development-loop/",
)


class SyncError(RuntimeError):
    """Raised when synchronization cannot proceed safely."""


def _build_managed_path(relative_path: Path, repo_root: Path) -> Path:
    if relative_path.is_absolute() or any(part == ".." for part in relative_path.parts):
        raise SyncError(f"Managed path must stay within the repository: {relative_path}")

    destination = repo_root / relative_path
    normalized = Path(os.path.normpath(destination))
    try:
        normalized.relative_to(repo_root)
    except ValueError as exc:
        raise SyncError(f"Managed path escapes the repository: {relative_path}") from exc
    return destination


def managed_area_description() -> str:
    return ", ".join(MANAGED_AREAS)


def _matches_any_prefix(relative_path: Path, prefixes: tuple[str, ...]) -> bool:
    """Match on whole path components, never on a bare character prefix.

    A prefix ending in "/" selects a directory and everything under it. Any other prefix
    must equal a full payload path. Character-prefix matching would let ".claude/shared/core/eng"
    silently select engineering.md, and "" select the entire payload.
    """
    posix_path = relative_path.as_posix()
    for prefix in prefixes:
        if prefix.endswith("/"):
            if posix_path.startswith(prefix):
                return True
        elif posix_path == prefix:
            return True
    return False


def selection_prefix_error(prefix: str) -> str | None:
    """Return why a selection prefix is unusable, or None when it is well formed."""
    if not prefix.strip():
        return "prefix is empty"
    if prefix != prefix.strip():
        return "prefix has leading or trailing whitespace"
    if "\\" in prefix:
        return "prefix must use forward slashes"
    if prefix.startswith("/"):
        return "prefix must be relative to the payload root"
    if any(part in {"..", "."} for part in prefix.split("/")):
        return "prefix must not contain '.' or '..'"
    return None


def _matches_area(relative_path: Path, pattern: str) -> bool:
    """Match a path against one area pattern, per component, allowing "*" within a component."""
    parts = relative_path.parts
    segments = pattern.rstrip("/").split("/")
    if pattern.endswith("/"):
        if len(parts) <= len(segments):
            return False  # the pattern names a directory, so the path must be inside it
        candidate = parts[: len(segments)]
    else:
        if len(parts) != len(segments):
            return False
        candidate = parts
    return all(fnmatch.fnmatchcase(part, seg) for part, seg in zip(candidate, segments))


def _is_within_managed_area(relative_path: Path) -> bool:
    return any(_matches_area(relative_path, pattern) for pattern in MANAGED_AREAS)


def _deletion_refusal_reason(relative_name: str, repo_root: Path) -> str | None:
    """Return why a manifest entry must not be deleted, or None when deletion is safe.

    Deletion is best effort. The manifest lives in a repository this project does not own, so an
    entry it cannot vouch for is skipped rather than acted on: refusing to delete is always safe,
    and the rewritten manifest simply stops claiming the entry, so the repository self-heals.
    """
    if not relative_name.strip():
        return "entry is empty"

    relative_path = Path(relative_name)
    if not _is_within_managed_area(relative_path):
        return f"entry is outside the managed area ({managed_area_description()})"

    try:
        destination = _build_managed_path(relative_path, repo_root)
    except SyncError as exc:
        return str(exc)

    if destination.is_symlink():
        return "entry is a symlink"

    try:
        _ensure_no_symlink_parents(destination, repo_root)
    except SyncError as exc:
        return str(exc)

    return None


def _ensure_no_symlink_parents(path: Path, repo_root: Path) -> None:
    current = path.parent
    while current != repo_root:
        if current.is_symlink():
            raise SyncError(f"Refusing to operate through symlinked managed path: {current}")
        current = current.parent


def load_previous_manifest(repo_root: Path) -> dict[str, Any]:
    manifest_path = repo_root / MANIFEST_RELATIVE_PATH
    if not manifest_path.exists():
        return {"files": []}

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SyncError("Existing manifest must contain a JSON object.")

    source = data.get("source")
    if source is not None and source != MANIFEST_SOURCE:
        return {"files": []}

    files = data.get("files", [])
    if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
        raise SyncError("Existing manifest must contain a string array in 'files'.")
    return data


def get_payload_files(
    payload_root: Path, include_prefixes: tuple[str, ...] | None = None
) -> list[Path]:
    """List payload files, optionally limited to those under one of include_prefixes.

    A prefix is matched against the payload-relative POSIX path, so ".claude/shared/"
    selects everything beneath it. None selects the whole payload.
    """
    if not payload_root.is_dir():
        raise SyncError(f"Payload root does not exist: {payload_root}")

    files: list[Path] = []
    for path in sorted(payload_root.rglob("*")):
        if path.is_symlink():
            raise SyncError(f"Payload contains a symlink: {path}")
        if not path.is_file():
            continue
        relative_path = path.relative_to(payload_root)
        if (
            include_prefixes is not None
            and not _matches_any_prefix(relative_path, REQUIRED_PAYLOAD_PATHS)
            and not _matches_any_prefix(relative_path, include_prefixes)
        ):
            continue
        files.append(relative_path)

    if include_prefixes is not None:
        # Checked per prefix, not per selection. A profile with five good prefixes and one typo
        # would otherwise pass silently and delete every file the dead prefix used to select,
        # because those files are still recorded in the downstream manifest.
        dead = [
            prefix
            for prefix in include_prefixes
            if not any(_matches_any_prefix(path, (prefix,)) for path in files)
        ]
        if dead:
            raise SyncError(f"Selection prefixes match no payload files: {dead}")
    return files


def remove_empty_parents(path: Path, stop_at: Path, repo_root: Path | None = None) -> None:
    current = path.parent
    stop_at = stop_at.resolve()
    floor = repo_root.resolve() if repo_root is not None else None

    while current.exists() and current.resolve() != stop_at:
        # Never walk out of the repository, even if handed a stop_at that is not an ancestor.
        if floor is not None and current.resolve() == floor:
            break
        if any(current.iterdir()):
            break
        current.rmdir()
        current = current.parent


def remove_stale_files(
    previous_files: list[str], current_files: list[Path], repo_root: Path
) -> list[str]:
    """Delete manifest-recorded files the payload no longer ships. Returns entries refused."""
    current_set = {path.as_posix() for path in current_files}
    stale_names = [name for name in sorted(previous_files) if name not in current_set]

    # Vet every entry before deleting any of them, so a refusal partway through cannot leave the
    # repository in a state neither manifest describes.
    deletions: list[Path] = []
    skipped: list[str] = []
    for relative_name in stale_names:
        reason = _deletion_refusal_reason(relative_name, repo_root)
        if reason is not None:
            skipped.append(relative_name)
            print(
                f"WARNING: refusing to delete manifest entry {relative_name!r}: {reason}",
                file=sys.stderr,
            )
            continue
        deletions.append(Path(relative_name))

    for relative_path in deletions:
        destination = repo_root / relative_path
        if destination.is_file():
            destination.unlink()
            # Stop at `.claude`, which is never removed, and never walk past the repository.
            remove_empty_parents(destination, (repo_root / ".claude").resolve(), repo_root)

    return skipped


def copy_payload(
    payload_root: Path, repo_root: Path, include_prefixes: tuple[str, ...] | None = None
) -> list[Path]:
    copied_files: list[Path] = []
    for relative_path in get_payload_files(payload_root, include_prefixes):
        if not _is_within_managed_area(relative_path):
            raise SyncError(
                f"Payload file is outside the managed area ({managed_area_description()}): "
                f"{relative_path.as_posix()}"
            )
        source = payload_root / relative_path
        destination = _build_managed_path(relative_path, repo_root)
        if destination.is_symlink():
            raise SyncError(f"Refusing to operate on symlinked managed path: {destination}")
        _ensure_no_symlink_parents(destination, repo_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink():
            raise SyncError(f"Refusing to operate on symlinked managed path: {destination}")
        _ensure_no_symlink_parents(destination, repo_root)
        shutil.copy2(source, destination)
        copied_files.append(relative_path)
    return copied_files


def write_manifest(repo_root: Path, version: str, files: list[Path]) -> None:
    manifest_path = repo_root / MANIFEST_RELATIVE_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": 1,
        "source": MANIFEST_SOURCE,
        "version": version,
        "files": [path.as_posix() for path in sorted(files)],
    }
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def detect_adoptions(
    current_files: list[Path], previous_files: list[str], repo_root: Path
) -> list[str]:
    """Payload destinations that already exist downstream but no manifest claimed.

    Either the downstream repository authored a file at a path this system owns, or a previous
    manifest became unreadable -- after a `source` change, for instance. The two are
    indistinguishable from the filesystem, so neither is refused: both are reported.
    """
    previously_claimed = set(previous_files)
    return [
        relative_path.as_posix()
        for relative_path in current_files
        if relative_path.as_posix() not in previously_claimed
        and (repo_root / relative_path).exists()
    ]


def sync_payload(
    payload_root: Path,
    repo_root: Path,
    version: str,
    include_prefixes: tuple[str, ...] | None = None,
) -> list[str]:
    """Synchronize the payload into repo_root.

    include_prefixes limits distribution to part of the payload. Narrowing it between runs
    removes the newly-excluded files downstream, because they are still recorded in the
    previous manifest and are absent from the current selection.
    """
    previous_manifest = load_previous_manifest(repo_root)
    previous_files = [str(item) for item in previous_manifest.get("files", [])]
    current_files = get_payload_files(payload_root, include_prefixes)

    adopted = detect_adoptions(current_files, previous_files, repo_root)
    for relative_name in adopted:
        print(
            f"WARNING: overwriting {relative_name!r}, which exists downstream but no manifest "
            "claimed. It is inside the area this system owns, so the write proceeds -- but it is "
            "reported rather than silent.",
            file=sys.stderr,
        )

    remove_stale_files(previous_files, current_files, repo_root)
    copy_payload(payload_root, repo_root, include_prefixes)
    write_manifest(repo_root, version, current_files)
    return adopted


__all__ = [
    "MANAGED_AREAS",
    "REQUIRED_PAYLOAD_PATHS",
    "selection_prefix_error",
    "detect_adoptions",
    "managed_area_description",
    "MANIFEST_RELATIVE_PATH",
    "MANIFEST_SOURCE",
    "SyncError",
    "copy_payload",
    "get_payload_files",
    "load_previous_manifest",
    "remove_empty_parents",
    "remove_stale_files",
    "sync_payload",
    "write_manifest",
]
