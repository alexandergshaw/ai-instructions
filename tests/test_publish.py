from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from publish import PublishError, branch_ref, commit_changes, configure_git_transport_auth, load_targets, push_branch, remote_branch_exists  # noqa: E402
from sync_payload import SyncError  # noqa: E402


class PublishTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_targets(self, payload: object) -> Path:
        path = self.workspace / "targets.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_load_targets_rejects_non_object_root(self) -> None:
        with self.assertRaises(PublishError):
            load_targets(self.write_targets([]))

    def test_load_targets_accepts_optional_fields(self) -> None:
        """`languages` was removed by BL-10; `profile` is the remaining optional field."""
        targets = load_targets(
            self.write_targets(
                {
                    "targets": [
                        {
                            "repo": "owner/repository",
                            "enabled": True,
                            "profile": "student-autograded",
                        }
                    ]
                }
            )
        )

        self.assertEqual(targets[0].profile, "student-autograded")

    def test_sync_error_in_one_target_does_not_abort_remaining_targets(self) -> None:
        """AGENTS.md: one downstream failure must not prevent attempts against the rest."""
        import publish

        processed: list[str] = []

        def fake_process_target(target, source_root, version, env, profiles=None):
            processed.append(target.repo)
            if target.repo == "owner/broken":
                raise SyncError("manifest names a path outside the managed area")
            return f"{target.repo}: ok"

        targets_file = self.write_targets(
            {
                "targets": [
                    {"repo": "owner/broken", "enabled": True},
                    {"repo": "owner/healthy", "enabled": True},
                ]
            }
        )

        env = {
            "GH_TOKEN": "token",
            "SOURCE_VERSION": "v1.0.0",
            "BOT_NAME": "bot",
            "BOT_EMAIL": "bot@example.com",
        }

        with patch.object(publish, "process_target", fake_process_target), patch.object(
            publish, "require_environment", lambda: env
        ), patch.object(publish, "configure_git_transport_auth", lambda _env: None), patch.object(
            publish, "load_targets", lambda _path: load_targets(targets_file)
        ), patch("builtins.print") as mock_print:
            exit_code = publish.main()

        self.assertEqual(processed, ["owner/broken", "owner/healthy"])
        self.assertEqual(exit_code, 1)
        # The healthy target must be recorded as a success, not merely attempted: a run that
        # marked every target failed would otherwise satisfy the assertions above.
        printed = "\n".join(
            str(call.args[0]) if call.args else "" for call in mock_print.call_args_list
        )
        self.assertIn("owner/healthy: ok", printed)
        self.assertIn("Successful targets: 1", printed)
        self.assertIn("Failed targets: 1", printed)

    def test_process_target_passes_the_profile_selection_to_sync(self) -> None:
        """The wiring between resolve_selection and sync_payload had no coverage."""
        import publish

        recorded: dict[str, object] = {}

        def fake_sync(payload_root, repo_root, version, include_prefixes=None):
            recorded["include_prefixes"] = include_prefixes

        target = publish.Target(repo="owner/repository", profile="minimal")
        profiles = {"minimal": (".claude/shared/",)}
        env = {"BOT_NAME": "bot", "BOT_EMAIL": "bot@example.com"}

        with patch.object(publish, "get_default_branch", lambda *a, **k: "main"), patch.object(
            publish, "clone_repository", lambda *a, **k: None
        ), patch.object(publish, "configure_git_identity", lambda *a, **k: None), patch.object(
            publish, "run_command", lambda *a, **k: ""
        ), patch.object(publish, "checkout_branch", lambda *a, **k: False), patch.object(
            publish, "load_previous_manifest", lambda *a, **k: {"files": []}
        ), patch.object(publish, "get_payload_files", lambda *a, **k: []), patch.object(
            publish, "sync_payload", fake_sync
        ), patch.object(publish, "repository_has_changes", lambda *a, **k: False):
            publish.process_target(target, self.workspace, "v1.0.0", env, profiles)

        self.assertEqual(recorded["include_prefixes"], (".claude/shared/",))

    def test_load_profiles_returns_empty_when_absent(self) -> None:
        import publish

        self.assertEqual(publish.load_profiles(self.workspace / "missing.json"), {})

    def test_load_profiles_reads_prefixes(self) -> None:
        import publish

        path = self.workspace / "profiles.json"
        path.write_text(
            json.dumps({"profiles": {"minimal": [".claude/shared/core/"]}}), encoding="utf-8"
        )

        self.assertEqual(publish.load_profiles(path), {"minimal": (".claude/shared/core/",)})

    def test_unknown_profile_is_rejected(self) -> None:
        import publish

        with self.assertRaisesRegex(PublishError, "unknown profile"):
            publish.resolve_selection(
                publish.Target(repo="owner/repository", profile="nope"), {"minimal": (".claude/",)}
            )

    def test_target_without_profile_selects_everything(self) -> None:
        import publish

        selection = publish.resolve_selection(
            publish.Target(repo="owner/repository"), {"minimal": (".claude/",)}
        )

        self.assertIsNone(selection)

    # --- BL-10: a schema promise nothing keeps is removed, loudly --------------------

    def test_languages_is_rejected_with_a_pointer_to_profiles(self) -> None:
        with self.assertRaisesRegex(PublishError, "profile"):
            load_targets(
                self.write_targets(
                    {"targets": [{"repo": "owner/repository", "languages": ["python"]}]}
                )
            )

    def test_a_target_without_languages_is_unaffected(self) -> None:
        targets = load_targets(
            self.write_targets({"targets": [{"repo": "owner/repository", "profile": "x"}]})
        )
        self.assertEqual(targets[0].profile, "x")

    # --- BL-08: the pull request says what changed ------------------------------------

    def test_the_pr_body_lists_what_changed(self) -> None:
        import publish

        body = publish.build_pr_body(
            version="v2.0.0",
            profile="standards-only",
            added=[".claude/shared/core/new.md"],
            modified=[".claude/shared/core/engineering.md"],
            removed=[".claude/shared/languages/cpp.md"],
            adopted=[],
        )

        self.assertIn(".claude/shared/core/new.md", body)
        self.assertIn(".claude/shared/languages/cpp.md", body)
        self.assertIn("standards-only", body)
        self.assertIn("Removed", body)

    def test_the_pr_body_marks_a_first_delivery_rather_than_an_update(self) -> None:
        import publish

        body = publish.build_pr_body(
            version="v2.0.0", profile=None,
            added=[".claude/shared/core/engineering.md"], modified=[], removed=[], adopted=[],
        )

        self.assertIn("first", body.lower())

    def test_the_pr_body_names_files_it_overwrote_that_no_manifest_claimed(self) -> None:
        import publish

        body = publish.build_pr_body(
            version="v2.0.0", profile=None, added=[], modified=[".claude/shared/x.md"],
            removed=[], adopted=[".claude/shared/x.md"],
        )

        self.assertIn("no manifest claimed", body.lower())

    def test_the_commit_subject_says_what_it_did(self) -> None:
        import publish

        only_removals = publish.build_commit_subject("v2.0.0", added=[], modified=[], removed=["a"])
        first = publish.build_commit_subject("v2.0.0", added=["a"], modified=[], removed=[])

        self.assertIn("remove", only_removals.lower())
        self.assertNotEqual(only_removals, first)

    # --- BL-18: every enabled target's last-received version is reported ---------------

    def test_fleet_report_distinguishes_never_received_from_behind(self) -> None:
        import publish

        lines = publish.format_fleet_report(
            {"owner/current": "v2.0.0", "owner/behind": "v1.0.0", "owner/absent": None},
            current_version="v2.0.0",
        )
        rendered = "\n".join(lines)

        self.assertIn("owner/absent", rendered)
        self.assertIn("no manifest", rendered.lower())
        self.assertIn("v1.0.0", rendered)
        self.assertNotEqual(
            [l for l in lines if "owner/absent" in l], [l for l in lines if "owner/behind" in l]
        )

    def test_fleet_report_is_quiet_when_every_target_is_current(self) -> None:
        import publish

        lines = publish.format_fleet_report(
            {"owner/a": "v2.0.0", "owner/b": "v2.0.0"}, current_version="v2.0.0"
        )

        self.assertTrue(all("behind" not in l.lower() for l in lines))

    @patch("publish.subprocess.run")
    def test_remote_branch_exists_uses_exact_ref(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")

        exists = remote_branch_exists(self.workspace, "automation/claude-instructions-v1.0.0", {})

        self.assertTrue(exists)
        command = mock_run.call_args.args[0]
        self.assertEqual(command[-1], branch_ref("automation/claude-instructions-v1.0.0"))

    @patch("publish.subprocess.run")
    def test_remote_branch_exists_raises_on_operational_failure(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="permission denied")

        with self.assertRaises(PublishError):
            remote_branch_exists(self.workspace, "automation/claude-instructions-v1.0.0", {})

    @patch("publish.subprocess.run")
    def test_remote_branch_exists_returns_false_for_no_matching_refs(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess([], 2, stdout="", stderr="")

        exists = remote_branch_exists(self.workspace, "automation/claude-instructions-v1.0.0", {})

        self.assertFalse(exists)

    @patch("publish.run_command")
    def test_push_branch_uses_force_with_lease_only_when_requested(self, mock_run_command) -> None:
        push_branch(self.workspace, "automation/claude-instructions-v1.0.0", {}, force_with_lease=False)
        push_branch(self.workspace, "automation/claude-instructions-v1.0.0", {}, force_with_lease=True)

        first_command = mock_run_command.call_args_list[0].args[0]
        second_command = mock_run_command.call_args_list[1].args[0]
        self.assertNotIn("--force-with-lease", first_command)
        self.assertIn("--force-with-lease", second_command)

    @patch("publish.run_command")
    def test_commit_changes_stages_only_managed_paths(self, mock_run_command) -> None:
        managed_file = self.workspace / ".claude/shared/core/engineering.md"
        manifest_file = self.workspace / ".claude/.central-instructions-manifest.json"
        managed_file.parent.mkdir(parents=True, exist_ok=True)
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        managed_file.write_text("content", encoding="utf-8")
        manifest_file.write_text("{}", encoding="utf-8")

        commit_changes(
            self.workspace,
            "v1.0.0",
            [Path(".claude/shared/core/engineering.md"), Path(".claude/.central-instructions-manifest.json")],
            {},
        )

        add_command = mock_run_command.call_args_list[0].args[0]
        self.assertEqual(add_command[:3], ["git", "add", "--"])
        self.assertIn(".claude/shared/core/engineering.md", add_command)
        self.assertIn(".claude/.central-instructions-manifest.json", add_command)
        self.assertNotIn(".", add_command)

    @patch("publish.run_command")
    def test_commit_changes_uses_git_rm_for_missing_managed_paths(self, mock_run_command) -> None:
        commit_changes(
            self.workspace,
            "v1.0.0",
            [Path(".claude/shared/core/engineering.md")],
            {},
        )

        rm_command = mock_run_command.call_args_list[0].args[0]
        self.assertEqual(rm_command[:4], ["git", "rm", "--quiet", "--ignore-unmatch"])
        self.assertIn(".claude/shared/core/engineering.md", rm_command)

    @patch("publish.run_command")
    def test_configure_git_transport_auth_uses_gh(self, mock_run_command) -> None:
        configure_git_transport_auth({})

        self.assertEqual(mock_run_command.call_args.args[0], ["gh", "auth", "setup-git"])


if __name__ == "__main__":
    unittest.main()
