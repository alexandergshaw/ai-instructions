from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sync_payload import MANIFEST_RELATIVE_PATH, SyncError, sync_payload  # noqa: E402


class SyncPayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.payload_root = self.workspace / "payload"
        self.repo_root = self.workspace / "target"
        self.payload_root.mkdir()
        self.repo_root.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_payload(self, relative_path: str, content: str) -> None:
        path = self.payload_root / Path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def read_manifest(self) -> dict[str, object]:
        return json.loads((self.repo_root / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))

    def test_fresh_synchronization_creates_files_and_manifest(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        self.write_payload(".claude/skills/shared-build-autograder/SKILL.md", "skill")

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertEqual(
            (self.repo_root / ".claude/shared/core/engineering.md").read_text(encoding="utf-8"),
            "engineering",
        )
        manifest = self.read_manifest()
        self.assertEqual(manifest["version"], "v1.0.0")
        self.assertIn(".claude/shared/core/engineering.md", manifest["files"])
        self.assertIn(".claude/skills/shared-build-autograder/SKILL.md", manifest["files"])

    def test_repeated_sync_is_idempotent(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")
        first_manifest = (self.repo_root / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")
        sync_payload(self.payload_root, self.repo_root, "v1.0.0")
        second_manifest = (self.repo_root / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8")

        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual((self.repo_root / ".claude/shared/core/engineering.md").read_text(encoding="utf-8"), "engineering")

    def test_existing_managed_file_is_updated(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "new")
        managed_file = self.repo_root / ".claude/shared/core/engineering.md"
        managed_file.parent.mkdir(parents=True, exist_ok=True)
        managed_file.write_text("old", encoding="utf-8")
        manifest_path = self.repo_root / MANIFEST_RELATIVE_PATH
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps({"schemaVersion": 1, "source": "central", "version": "v0.1.0", "files": [".claude/shared/core/engineering.md"]}),
            encoding="utf-8",
        )

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertEqual(managed_file.read_text(encoding="utf-8"), "new")

    def test_adding_new_payload_file_adds_it_to_repo(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        sync_payload(self.payload_root, self.repo_root, "v1.0.0")
        self.write_payload(".claude/shared/testing/general.md", "testing")

        sync_payload(self.payload_root, self.repo_root, "v1.1.0")

        self.assertTrue((self.repo_root / ".claude/shared/testing/general.md").is_file())
        self.assertEqual(self.read_manifest()["version"], "v1.1.0")

    def test_removed_managed_file_is_deleted(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        self.write_payload(".claude/shared/testing/general.md", "testing")
        sync_payload(self.payload_root, self.repo_root, "v1.0.0")
        (self.payload_root / ".claude/shared/testing/general.md").unlink()

        sync_payload(self.payload_root, self.repo_root, "v1.1.0")

        self.assertFalse((self.repo_root / ".claude/shared/testing/general.md").exists())
        self.assertTrue((self.repo_root / ".claude/shared/core/engineering.md").exists())

    def test_symlinked_managed_destination_is_rejected(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        external_file = self.workspace / "outside.md"
        external_file.write_text("outside", encoding="utf-8")
        managed_file = self.repo_root / ".claude/shared/core/engineering.md"
        managed_file.parent.mkdir(parents=True, exist_ok=True)
        managed_file.symlink_to(external_file)

        with self.assertRaises(SyncError):
            sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertEqual(external_file.read_text(encoding="utf-8"), "outside")

    def test_unmanaged_claude_files_are_preserved(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        unmanaged = self.repo_root / ".claude/local/custom.md"
        unmanaged.parent.mkdir(parents=True, exist_ok=True)
        unmanaged.write_text("keep me", encoding="utf-8")

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertEqual(unmanaged.read_text(encoding="utf-8"), "keep me")

    def test_downstream_root_claude_md_is_preserved(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        downstream_claude = self.repo_root / "CLAUDE.md"
        downstream_claude.write_text("repository specific", encoding="utf-8")

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertEqual(downstream_claude.read_text(encoding="utf-8"), "repository specific")

    def test_unmanaged_skill_is_preserved(self) -> None:
        self.write_payload(".claude/skills/shared-build-autograder/SKILL.md", "managed")
        unmanaged_skill = self.repo_root / ".claude/skills/local-skill/SKILL.md"
        unmanaged_skill.parent.mkdir(parents=True, exist_ok=True)
        unmanaged_skill.write_text("local", encoding="utf-8")

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertEqual(unmanaged_skill.read_text(encoding="utf-8"), "local")

    def test_manifest_version_is_updated(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")
        sync_payload(self.payload_root, self.repo_root, "v1.2.0")

        self.assertEqual(self.read_manifest()["version"], "v1.2.0")

    def test_required_directories_are_created(self) -> None:
        self.write_payload(".claude/shared/testing/general.md", "testing")

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertTrue((self.repo_root / ".claude/shared/testing").is_dir())
        self.assertTrue((self.repo_root / ".claude").is_dir())


if __name__ == "__main__":
    unittest.main()
