from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sync_payload import (  # noqa: E402
    MANIFEST_RELATIVE_PATH,
    MANIFEST_SOURCE,
    SyncError,
    copy_payload,
    get_payload_files,
    sync_payload,
)


def _detect_symlink_support() -> bool:
    """Report whether this platform lets the current user create symlinks."""
    with tempfile.TemporaryDirectory() as probe_dir:
        probe_root = Path(probe_dir)
        probe_target = probe_root / "target.txt"
        probe_target.write_text("probe", encoding="utf-8")
        try:
            (probe_root / "link.txt").symlink_to(probe_target)
        except (NotImplementedError, OSError):
            return False
    return True


SYMLINKS_SUPPORTED = _detect_symlink_support()


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

    def write_manifest_files(self, files: list[str]) -> None:
        manifest_path = self.repo_root / MANIFEST_RELATIVE_PATH
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "source": MANIFEST_SOURCE,
                    "version": "v0.9.0",
                    "files": files,
                }
            ),
            encoding="utf-8",
        )

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

    def test_foreign_manifest_does_not_authorize_deletion(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        foreign_file = self.repo_root / ".claude/shared/testing/general.md"
        foreign_file.parent.mkdir(parents=True, exist_ok=True)
        foreign_file.write_text("foreign", encoding="utf-8")
        manifest_path = self.repo_root / MANIFEST_RELATIVE_PATH
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "source": "another-tool",
                    "version": "v9.9.9",
                    "files": [".claude/shared/testing/general.md"],
                }
            ),
            encoding="utf-8",
        )

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertEqual(foreign_file.read_text(encoding="utf-8"), "foreign")
        self.assertEqual(self.read_manifest()["source"], "central-claude-instructions")

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

    def test_manifest_entry_outside_managed_roots_is_skipped_not_deleted(self) -> None:
        """A manifest is untrusted input; it may not authorize deletions outside .claude/."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        (self.repo_root / "CLAUDE.md").write_text("downstream owned", encoding="utf-8")
        (self.repo_root / "src").mkdir()
        (self.repo_root / "src" / "main.py").write_text("code", encoding="utf-8")
        self.write_manifest_files(["CLAUDE.md", "src/main.py"])

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertEqual((self.repo_root / "CLAUDE.md").read_text(encoding="utf-8"), "downstream owned")
        self.assertEqual((self.repo_root / "src/main.py").read_text(encoding="utf-8"), "code")
        # The rewritten manifest stops claiming the entries, so the repository self-heals.
        self.assertEqual(self.read_manifest()["files"], [".claude/shared/core/engineering.md"])

    def test_refused_entry_does_not_block_delivery_or_later_syncs(self) -> None:
        """A malformed manifest must not freeze a downstream repository."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        self.write_manifest_files(["CLAUDE.md"])

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")
        self.assertTrue((self.repo_root / ".claude/shared/core/engineering.md").is_file())

        sync_payload(self.payload_root, self.repo_root, "v1.1.0")
        self.assertEqual(self.read_manifest()["version"], "v1.1.0")

    def test_stale_entry_is_deleted_even_when_another_entry_is_refused(self) -> None:
        """Vetting happens up front: one bad entry must not abort legitimate cleanup."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        stale = self.repo_root / ".claude/shared/legacy/removed.md"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("stale", encoding="utf-8")
        (self.repo_root / "CLAUDE.md").write_text("downstream owned", encoding="utf-8")
        self.write_manifest_files([".claude/shared/legacy/removed.md", "CLAUDE.md"])

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertFalse(stale.exists())
        self.assertEqual((self.repo_root / "CLAUDE.md").read_text(encoding="utf-8"), "downstream owned")

    def test_no_partial_deletion_when_a_later_entry_is_refused(self) -> None:
        """A traversal entry sorts after a legitimate one; the legitimate one must still be safe."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        stale = self.repo_root / ".claude/shared/legacy/removed.md"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("stale", encoding="utf-8")
        (self.repo_root / "CLAUDE.md").write_text("downstream owned", encoding="utf-8")
        self.write_manifest_files([".claude/shared/legacy/removed.md", ".claude/zz/../../CLAUDE.md"])

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertEqual((self.repo_root / "CLAUDE.md").read_text(encoding="utf-8"), "downstream owned")
        self.assertNotIn(".claude/zz/../../CLAUDE.md", self.read_manifest()["files"])

    def test_managed_root_must_be_the_first_path_component(self) -> None:
        """'.claude' buried deeper in a path does not make the entry ours to delete."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        impostor = self.repo_root / "src/.claude/notes.md"
        impostor.parent.mkdir(parents=True, exist_ok=True)
        impostor.write_text("downstream owned", encoding="utf-8")
        self.write_manifest_files(["src/.claude/notes.md"])

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertEqual(impostor.read_text(encoding="utf-8"), "downstream owned")

    def test_empty_manifest_entry_is_harmless(self) -> None:
        """A blank entry is bad-merge debris, not a reason to stop delivering."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        self.write_manifest_files(["", "   "])

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertTrue((self.repo_root / ".claude/shared/core/engineering.md").is_file())

    def test_manifest_entry_inside_managed_root_is_still_deleted(self) -> None:
        """The containment check must not break legitimate stale cleanup."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        stale = self.repo_root / ".claude/shared/testing/general.md"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("stale", encoding="utf-8")
        self.write_manifest_files([".claude/shared/testing/general.md"])

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertFalse(stale.exists())

    def test_payload_file_outside_managed_roots_is_rejected(self) -> None:
        """Distribution is bounded by the same roots as cleanup, so the two cannot drift."""
        self.write_payload(".github/workflows/ci.yml", "central ci")

        with self.assertRaisesRegex(SyncError, "outside the managed area"):
            copy_payload(self.payload_root, self.repo_root)

    def test_no_selection_distributes_the_whole_payload(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        self.write_payload(".claude/skills/shared-loop/SKILL.md", "loop")

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertTrue((self.repo_root / ".claude/shared/core/engineering.md").is_file())
        self.assertTrue((self.repo_root / ".claude/skills/shared-loop/SKILL.md").is_file())

    def test_selection_limits_what_is_distributed(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        self.write_payload(".claude/skills/shared-loop/SKILL.md", "loop")

        sync_payload(
            self.payload_root, self.repo_root, "v1.0.0", include_prefixes=(".claude/shared/",)
        )

        self.assertTrue((self.repo_root / ".claude/shared/core/engineering.md").is_file())
        self.assertFalse((self.repo_root / ".claude/skills/shared-loop/SKILL.md").exists())
        self.assertEqual(self.read_manifest()["files"], [".claude/shared/core/engineering.md"])

    def test_narrowing_the_selection_removes_previously_distributed_files(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        self.write_payload(".claude/skills/shared-loop/SKILL.md", "loop")
        unmanaged = self.repo_root / ".claude/local/custom.md"
        unmanaged.parent.mkdir(parents=True, exist_ok=True)
        unmanaged.write_text("downstream owned", encoding="utf-8")

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")
        self.assertTrue((self.repo_root / ".claude/skills/shared-loop/SKILL.md").is_file())

        sync_payload(
            self.payload_root, self.repo_root, "v1.1.0", include_prefixes=(".claude/shared/",)
        )

        self.assertFalse((self.repo_root / ".claude/skills/shared-loop/SKILL.md").exists())
        self.assertTrue((self.repo_root / ".claude/shared/core/engineering.md").is_file())
        self.assertEqual(unmanaged.read_text(encoding="utf-8"), "downstream owned")

    def test_selection_is_idempotent(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        self.write_payload(".claude/skills/shared-loop/SKILL.md", "loop")
        selection = (".claude/shared/",)

        sync_payload(self.payload_root, self.repo_root, "v1.0.0", include_prefixes=selection)
        first = self.read_manifest()
        sync_payload(self.payload_root, self.repo_root, "v1.0.0", include_prefixes=selection)

        self.assertEqual(first, self.read_manifest())

    def test_get_payload_files_filters_by_prefix(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        self.write_payload(".claude/skills/shared-loop/SKILL.md", "loop")

        selected = get_payload_files(self.payload_root, include_prefixes=(".claude/skills/",))

        self.assertEqual([path.as_posix() for path in selected], [".claude/skills/shared-loop/SKILL.md"])

    def test_selection_matching_nothing_is_rejected(self) -> None:
        """A selection that ships nothing is a configuration mistake, not an empty sync."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")

        with self.assertRaisesRegex(SyncError, "match no payload files"):
            sync_payload(
                self.payload_root, self.repo_root, "v1.0.0", include_prefixes=(".claude/nothing/",)
            )

    def test_a_dead_prefix_is_rejected_even_when_another_matches(self) -> None:
        """One typo must not silently drop the files its prefix used to select."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        self.write_payload(".claude/shared/languages/python.md", "python")

        with self.assertRaisesRegex(SyncError, "match no payload files"):
            sync_payload(
                self.payload_root,
                self.repo_root,
                "v1.0.0",
                include_prefixes=(".claude/shared/core/", ".claude/shared/langauges/"),
            )

    def test_a_dead_selection_deletes_nothing_from_a_populated_repository(self) -> None:
        """The guard must run before any deletion, not merely raise eventually."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        self.write_payload(".claude/shared/languages/python.md", "python")
        sync_payload(self.payload_root, self.repo_root, "v1.0.0")
        before = sorted(
            path.relative_to(self.repo_root).as_posix()
            for path in self.repo_root.rglob("*")
            if path.is_file()
        )
        manifest_before = self.read_manifest()

        with self.assertRaises(SyncError):
            sync_payload(
                self.payload_root, self.repo_root, "v1.0.0", include_prefixes=(".claude/gone/",)
            )

        after = sorted(
            path.relative_to(self.repo_root).as_posix()
            for path in self.repo_root.rglob("*")
            if path.is_file()
        )
        self.assertEqual(before, after)
        self.assertEqual(manifest_before, self.read_manifest())

    def test_prefixes_match_whole_path_components(self) -> None:
        """A character prefix must not select a file it merely shares letters with."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")

        with self.assertRaisesRegex(SyncError, "match no payload files"):
            get_payload_files(self.payload_root, include_prefixes=(".claude/shared/core/eng",))

    def test_the_floor_is_distributed_whatever_the_selection_excludes(self) -> None:
        self.write_payload(".claude/skills/shared-agent-floor/SKILL.md", "the floor")
        self.write_payload(".claude/shared/languages/python.md", "python")

        sync_payload(
            self.payload_root,
            self.repo_root,
            "v1.0.0",
            include_prefixes=(".claude/shared/languages/",),
        )

        self.assertTrue((self.repo_root / ".claude/skills/shared-agent-floor/SKILL.md").is_file())

    @unittest.skipUnless(SYMLINKS_SUPPORTED, "Platform does not permit creating symlinks.")
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
