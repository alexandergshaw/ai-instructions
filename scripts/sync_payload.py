from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

MANIFEST_RELATIVE_PATH = Path(".claude/.central-instructions-manifest.json")
MANIFEST_SOURCE = "central-claude-instructions"

# Top-level downstream directories this system is permitted to delete from. The manifest that
# authorizes deletions lives inside the downstream repository, so it is untrusted input: it can be
# corrupted or hand-edited, and without this bound it could name any repository-relative path.
# Extend this tuple only alongside the corresponding payload area, so that cleanup stays symmetric
# with distribution.
MANAGED_ROOTS = (".claude",)


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
    return ", ".join(f"{root}/" for root in MANAGED_ROOTS)


def _is_within_managed_roots(relative_path: Path) -> bool:
    parts = relative_path.parts
    return bool(parts) and parts[0] in MANAGED_ROOTS


def _deletion_refusal_reason(relative_name: str, repo_root: Path) -> str | None:
    """Return why a manifest entry must not be deleted, or None when deletion is safe.

    Deletion is best effort. The manifest lives in a repository this project does not own, so an
    entry it cannot vouch for is skipped rather than acted on: refusing to delete is always safe,
    and the rewritten manifest simply stops claiming the entry, so the repository self-heals.
    """
    if not relative_name.strip():
        return "entry is empty"

    relative_path = Path(relative_name)
    if not _is_within_managed_roots(relative_path):
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


def get_payload_files(payload_root: Path) -> list[Path]:
    if not payload_root.is_dir():
        raise SyncError(f"Payload root does not exist: {payload_root}")

    files: list[Path] = []
    for path in sorted(payload_root.rglob("*")):
        if path.is_symlink():
            raise SyncError(f"Payload contains a symlink: {path}")
        if path.is_file():
            files.append(path.relative_to(payload_root))
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
            # Stop at the entry's own managed root so cleanup stays correct if MANAGED_ROOTS grows.
            remove_empty_parents(destination, (repo_root / relative_path.parts[0]).resolve(), repo_root)

    return skipped


def copy_payload(payload_root: Path, repo_root: Path) -> list[Path]:
    copied_files: list[Path] = []
    for relative_path in get_payload_files(payload_root):
        if not _is_within_managed_roots(relative_path):
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


def sync_payload(payload_root: Path, repo_root: Path, version: str) -> None:
    previous_manifest = load_previous_manifest(repo_root)
    previous_files = [str(item) for item in previous_manifest.get("files", [])]
    current_files = get_payload_files(payload_root)

    remove_stale_files(previous_files, current_files, repo_root)
    copied_files = copy_payload(payload_root, repo_root)
    write_manifest(repo_root, version, copied_files)


__all__ = [
    "MANAGED_ROOTS",
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
