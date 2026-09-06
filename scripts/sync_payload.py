from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

MANIFEST_RELATIVE_PATH = Path(".claude/.central-instructions-manifest.json")
MANIFEST_SOURCE = "central-claude-instructions"


class SyncError(RuntimeError):
    """Raised when synchronization cannot proceed safely."""


def _ensure_within_repo(path: Path, repo_root: Path) -> None:
    path.resolve().relative_to(repo_root.resolve())


def load_previous_manifest(repo_root: Path) -> dict[str, Any]:
    manifest_path = repo_root / MANIFEST_RELATIVE_PATH
    if not manifest_path.exists():
        return {"files": []}

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SyncError("Existing manifest must contain a JSON object.")

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


def remove_empty_parents(path: Path, stop_at: Path) -> None:
    current = path.parent
    stop_at = stop_at.resolve()

    while current.exists() and current.resolve() != stop_at:
        if any(current.iterdir()):
            break
        current.rmdir()
        current = current.parent


def remove_stale_files(previous_files: list[str], current_files: list[Path], repo_root: Path) -> None:
    current_set = {path.as_posix() for path in current_files}
    managed_root = (repo_root / ".claude").resolve()

    for relative_name in sorted(previous_files):
        if relative_name in current_set:
            continue

        destination = repo_root / Path(relative_name)
        _ensure_within_repo(destination, repo_root)
        if destination.is_symlink():
            raise SyncError(f"Refusing to delete symlinked managed path: {destination}")
        if destination.exists() and destination.is_file():
            destination.unlink()
            remove_empty_parents(destination, managed_root)


def copy_payload(payload_root: Path, repo_root: Path) -> list[Path]:
    copied_files: list[Path] = []
    for relative_path in get_payload_files(payload_root):
        source = payload_root / relative_path
        destination = repo_root / relative_path
        _ensure_within_repo(destination, repo_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
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
