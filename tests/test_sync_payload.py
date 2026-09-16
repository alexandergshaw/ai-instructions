from __future__ import annotations

import json
import os
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

    def write_manifest_files(self, files: list[str], schema_version: int | None = 1) -> None:
        manifest_path = self.repo_root / MANIFEST_RELATIVE_PATH
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        document: dict[str, object] = {}
        if schema_version is not None:
            document["schemaVersion"] = schema_version
        manifest_path.write_text(
            json.dumps(
                {
                    **document,
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

    # --- BL-02: deletion is bounded to the documented ownership boundary -------------

    def test_downstream_authored_claude_content_is_not_deletable(self) -> None:
        """`.claude/` is not the boundary. README documents shared/** and skills/shared-*/**."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        local = self.repo_root / ".claude/local/custom.md"
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text("downstream authored", encoding="utf-8")
        own_skill = self.repo_root / ".claude/skills/local-only/SKILL.md"
        own_skill.parent.mkdir(parents=True, exist_ok=True)
        own_skill.write_text("downstream skill", encoding="utf-8")
        self.write_manifest_files([".claude/local/custom.md", ".claude/skills/local-only/SKILL.md"])

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertEqual(local.read_text(encoding="utf-8"), "downstream authored")
        self.assertEqual(own_skill.read_text(encoding="utf-8"), "downstream skill")

    def test_stale_file_inside_the_boundary_is_still_deleted(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        stale_shared = self.repo_root / ".claude/shared/legacy/old.md"
        stale_shared.parent.mkdir(parents=True, exist_ok=True)
        stale_shared.write_text("stale", encoding="utf-8")
        stale_skill = self.repo_root / ".claude/skills/shared-gone/SKILL.md"
        stale_skill.parent.mkdir(parents=True, exist_ok=True)
        stale_skill.write_text("stale", encoding="utf-8")
        self.write_manifest_files(
            [".claude/shared/legacy/old.md", ".claude/skills/shared-gone/SKILL.md"]
        )

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertFalse(stale_shared.exists())
        self.assertFalse(stale_skill.exists())

    def test_refusing_an_out_of_boundary_entry_stays_non_fatal(self) -> None:
        """Delivery continues and the manifest self-heals, as for any refused entry."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        local = self.repo_root / ".claude/local/custom.md"
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text("downstream authored", encoding="utf-8")
        self.write_manifest_files([".claude/local/custom.md"])

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertTrue((self.repo_root / ".claude/shared/core/engineering.md").is_file())
        self.assertNotIn(".claude/local/custom.md", self.read_manifest()["files"])

    # --- BL-01: overwriting inside the boundary is reported, never silent ------------

    def test_overwriting_an_unmanaged_file_is_reported(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "central")
        squatter = self.repo_root / ".claude/shared/core/engineering.md"
        squatter.parent.mkdir(parents=True, exist_ok=True)
        squatter.write_text("authored downstream before we shipped one", encoding="utf-8")

        adopted = sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertIn(".claude/shared/core/engineering.md", adopted)
        self.assertEqual(squatter.read_text(encoding="utf-8"), "central")

    def test_updating_a_managed_file_is_not_reported_as_adoption(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "v2")
        managed = self.repo_root / ".claude/shared/core/engineering.md"
        managed.parent.mkdir(parents=True, exist_ok=True)
        managed.write_text("v1", encoding="utf-8")
        self.write_manifest_files([".claude/shared/core/engineering.md"])

        adopted = sync_payload(self.payload_root, self.repo_root, "v1.1.0")

        self.assertEqual(adopted, [])
        self.assertEqual(managed.read_text(encoding="utf-8"), "v2")

    def test_re_adoption_after_a_source_change_still_delivers_everything(self) -> None:
        """The manifest reads as empty, but the files are ours. Delivery must not stop."""
        import json

        self.write_payload(".claude/shared/core/engineering.md", "v2")
        self.write_payload(".claude/shared/languages/python.md", "v2")
        for name in ("core/engineering.md", "languages/python.md"):
            path = self.repo_root / f".claude/shared/{name}"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("v1", encoding="utf-8")
        manifest = self.repo_root / MANIFEST_RELATIVE_PATH
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            json.dumps({"schemaVersion": 1, "source": "a-previous-name", "files": []}),
            encoding="utf-8",
        )

        adopted = sync_payload(self.payload_root, self.repo_root, "v2.0.0")

        for name in ("core/engineering.md", "languages/python.md"):
            path = self.repo_root / f".claude/shared/{name}"
            self.assertEqual(path.read_text(encoding="utf-8"), "v2")
        self.assertEqual(len(adopted), 2)

    # --- BL-11: an unreadable manifest shape authorizes nothing ----------------------

    def test_unknown_schema_version_authorizes_no_deletion(self) -> None:
        """A shape we cannot read must not be acted on -- but must not stop delivery either."""
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        stale = self.repo_root / ".claude/shared/legacy/old.md"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("would be deleted under a readable manifest", encoding="utf-8")
        self.write_manifest_files([".claude/shared/legacy/old.md"], schema_version=99)

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertTrue(stale.exists())
        self.assertTrue((self.repo_root / ".claude/shared/core/engineering.md").is_file())

    def test_unknown_schema_version_self_heals_on_the_next_run(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        self.write_manifest_files([".claude/shared/legacy/old.md"], schema_version=99)

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertEqual(self.read_manifest()["schemaVersion"], 1)

    def test_the_current_schema_version_still_authorizes_deletion(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        stale = self.repo_root / ".claude/shared/legacy/old.md"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("stale", encoding="utf-8")
        self.write_manifest_files([".claude/shared/legacy/old.md"], schema_version=1)

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertFalse(stale.exists())

    def test_a_manifest_without_a_schema_version_behaves_as_before(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        stale = self.repo_root / ".claude/shared/legacy/old.md"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("stale", encoding="utf-8")
        self.write_manifest_files([".claude/shared/legacy/old.md"], schema_version=None)

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertFalse(stale.exists())

    # --- BL-15: the deletion path's symlink refusals. A copy-path symlink test already
    # existed; the deletion path had none on any platform. -----------------------------

    @unittest.skipIf(os.name == "nt", "Windows is the platform these guards legitimately skip on.")
    def test_symlinks_can_actually_be_created_on_posix(self) -> None:
        """BL-15 closes only if the symlink tests RUN somewhere. CI is Linux; prove it there.

        If symlink creation ever stops working on the runner, every symlink guard in this file
        turns into a skip and `OK (skipped=N)` still reads as green. This asserts the real
        precondition by doing it, rather than asserting a module-level probe result.
        """
        link = self.workspace / "probe-link.md"
        target = self.workspace / "probe-target.md"
        target.write_text("probe", encoding="utf-8")

        link.symlink_to(target)

        self.assertTrue(link.is_symlink())
        self.assertEqual(link.read_text(encoding="utf-8"), "probe")

    @unittest.skipUnless(SYMLINKS_SUPPORTED, "Platform does not permit creating symlinks.")
    def test_stale_entry_that_is_a_symlink_is_refused_not_followed(self) -> None:
        """Deleting a symlink the manifest names would be ordinary. Following it is not.

        The manifest is untrusted input, so an entry pointing outside the repository must not
        become a way to unlink a file the central system was never given authority over.
        """
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        external_file = self.workspace / "outside.md"
        external_file.write_text("outside", encoding="utf-8")
        stale_link = self.repo_root / ".claude/shared/legacy/old.md"
        stale_link.parent.mkdir(parents=True, exist_ok=True)
        stale_link.symlink_to(external_file)
        self.write_manifest_files([".claude/shared/legacy/old.md"])

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertTrue(external_file.is_file())
        self.assertEqual(external_file.read_text(encoding="utf-8"), "outside")
        self.assertTrue(stale_link.is_symlink())
        # Delivery continued, and the manifest stopped claiming what it could not vouch for.
        self.assertTrue((self.repo_root / ".claude/shared/core/engineering.md").is_file())
        self.assertNotIn(".claude/shared/legacy/old.md", self.read_manifest()["files"])

    @unittest.skipUnless(SYMLINKS_SUPPORTED, "Platform does not permit creating symlinks.")
    def test_stale_entry_under_a_symlinked_parent_is_refused(self) -> None:
        self.write_payload(".claude/shared/core/engineering.md", "engineering")
        external_dir = self.workspace / "elsewhere"
        external_dir.mkdir()
        (external_dir / "old.md").write_text("outside", encoding="utf-8")
        managed_parent = self.repo_root / ".claude/shared/legacy"
        managed_parent.parent.mkdir(parents=True, exist_ok=True)
        managed_parent.symlink_to(external_dir, target_is_directory=True)
        self.write_manifest_files([".claude/shared/legacy/old.md"])

        sync_payload(self.payload_root, self.repo_root, "v1.0.0")

        self.assertTrue((external_dir / "old.md").is_file())

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
