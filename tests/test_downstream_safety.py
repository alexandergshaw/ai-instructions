"""End-to-end downstream-safety harness.

The unit tests in ``test_sync_payload`` exercise synchronization against small synthetic
payloads. This harness runs the same guarantees against the payload this repository actually
ships, in a temporary directory that stands in for a downstream repository.

These are the invariants that justify letting automation write into repositories this project
does not control. ``DEVELOPMENT-LOOP.md`` requires them at tier T3.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sync_payload import MANIFEST_RELATIVE_PATH, MANIFEST_SOURCE, sync_payload  # noqa: E402

PAYLOAD_ROOT = ROOT / "payload"
DOWNSTREAM_CLAUDE_MD = "# Downstream CLAUDE.md\n\nOwned by the downstream repository.\n"


class DownstreamSafetyTests(unittest.TestCase):
    """Prove the shipped payload syncs without disturbing downstream-owned content."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.repo_root = self.workspace / "downstream"
        self.repo_root.mkdir()
        self._build_downstream_fixture()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _build_downstream_fixture(self) -> None:
        """Create a downstream repository holding content the central repo must never own."""
        self._write(".claude/local/custom.md", "A locally authored rule.\n")
        self._write(".claude/skills/local-only/SKILL.md", "A skill the downstream repo owns.\n")
        self._write("CLAUDE.md", DOWNSTREAM_CLAUDE_MD)
        self._write("src/main.py", "print('downstream code')\n")
        self._write("README.md", "# Downstream project\n")

    def _write(self, relative_path: str, content: str) -> None:
        path = self.repo_root / Path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _snapshot(self) -> dict[str, str]:
        """Hash every file in the downstream repository, keyed by relative path."""
        return {
            path.relative_to(self.repo_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.repo_root.rglob("*"))
            if path.is_file()
        }

    def _payload_copy_without(self, relative_path: str) -> Path:
        """Copy the shipped payload into the workspace with one file removed."""
        trimmed_root = self.workspace / "trimmed-payload"
        if trimmed_root.exists():
            shutil.rmtree(trimmed_root)
        shutil.copytree(PAYLOAD_ROOT, trimmed_root)
        (trimmed_root / relative_path).unlink()
        return trimmed_root

    def test_shipped_payload_syncs_and_is_idempotent(self) -> None:
        sync_payload(PAYLOAD_ROOT, self.repo_root, "v1.0.0")
        first = self._snapshot()
        sync_payload(PAYLOAD_ROOT, self.repo_root, "v1.0.0")

        self.assertEqual(first, self._snapshot())
        self.assertTrue((self.repo_root / MANIFEST_RELATIVE_PATH).is_file())

    def test_downstream_owned_content_survives_a_sync(self) -> None:
        before = self._snapshot()

        sync_payload(PAYLOAD_ROOT, self.repo_root, "v1.0.0")

        for relative_path in (
            "CLAUDE.md",
            ".claude/local/custom.md",
            ".claude/skills/local-only/SKILL.md",
            "src/main.py",
            "README.md",
        ):
            with self.subTest(path=relative_path):
                self.assertIn(relative_path, self._snapshot())
                self.assertEqual(before[relative_path], self._snapshot()[relative_path])

    def test_sync_only_adds_paths_it_manages(self) -> None:
        before = set(self._snapshot())

        sync_payload(PAYLOAD_ROOT, self.repo_root, "v1.0.0")

        added = set(self._snapshot()) - before
        self.assertTrue(added, "Syncing the shipped payload should add files.")
        for relative_path in added:
            with self.subTest(path=relative_path):
                self.assertTrue(relative_path.startswith(".claude/"))

    def test_file_dropped_from_payload_is_removed_without_disturbing_siblings(self) -> None:
        dropped = ".claude/shared/languages/sql.md"
        sibling = ".claude/shared/languages/python.md"
        sync_payload(PAYLOAD_ROOT, self.repo_root, "v1.0.0")
        self.assertTrue((self.repo_root / dropped).is_file())
        sibling_before = (self.repo_root / sibling).read_bytes()

        trimmed_payload = self._payload_copy_without(dropped)
        sync_payload(trimmed_payload, self.repo_root, "v1.1.0")

        self.assertFalse((self.repo_root / dropped).exists())
        self.assertEqual((self.repo_root / sibling).read_bytes(), sibling_before)
        self.assertEqual((self.repo_root / "CLAUDE.md").read_text(encoding="utf-8"), DOWNSTREAM_CLAUDE_MD)
        self.assertTrue((self.repo_root / ".claude/local/custom.md").is_file())

    def test_untracked_managed_lookalike_is_not_deleted(self) -> None:
        """A file the manifest never listed is not the central repo's to remove."""
        impostor = ".claude/shared/languages/rust.md"
        sync_payload(PAYLOAD_ROOT, self.repo_root, "v1.0.0")
        self._write(impostor, "Authored downstream, never centrally managed.\n")

        sync_payload(PAYLOAD_ROOT, self.repo_root, "v1.1.0")

        self.assertTrue((self.repo_root / impostor).is_file())

    def test_manifest_naming_paths_outside_claude_deletes_nothing(self) -> None:
        """The manifest lives in a repository this project does not own."""
        manifest_path = self.repo_root / MANIFEST_RELATIVE_PATH
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "source": MANIFEST_SOURCE,
                    "version": "v0.9.0",
                    "files": ["CLAUDE.md", "src/main.py", "README.md"],
                }
            ),
            encoding="utf-8",
        )
        before = self._snapshot()

        sync_payload(PAYLOAD_ROOT, self.repo_root, "v1.0.0")

        manifest = json.loads((self.repo_root / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
        for refused in ("CLAUDE.md", "src/main.py", "README.md"):
            self.assertNotIn(refused, manifest["files"])

        for relative_path in ("CLAUDE.md", "src/main.py", "README.md"):
            with self.subTest(path=relative_path):
                self.assertTrue((self.repo_root / relative_path).is_file())
                self.assertEqual(before[relative_path], self._snapshot()[relative_path])

    def test_claude_directory_survives_removal_of_every_managed_file(self) -> None:
        sync_payload(PAYLOAD_ROOT, self.repo_root, "v1.0.0")
        empty_payload = self.workspace / "empty-payload"
        empty_payload.mkdir()

        sync_payload(empty_payload, self.repo_root, "v2.0.0")

        self.assertTrue((self.repo_root / ".claude").is_dir())
        self.assertTrue((self.repo_root / ".claude/local/custom.md").is_file())
        self.assertTrue((self.repo_root / ".claude/skills/local-only/SKILL.md").is_file())
        self.assertEqual((self.repo_root / "CLAUDE.md").read_text(encoding="utf-8"), DOWNSTREAM_CLAUDE_MD)


if __name__ == "__main__":
    unittest.main()
