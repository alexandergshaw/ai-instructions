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

from publish import PublishError, branch_ref, load_targets, push_branch, remote_branch_exists  # noqa: E402


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

    def test_load_targets_accepts_future_optional_fields(self) -> None:
        targets = load_targets(
            self.write_targets(
                {
                    "targets": [
                        {
                            "repo": "owner/repository",
                            "enabled": True,
                            "profile": "student-autograded",
                            "languages": ["python", "sql"],
                        }
                    ]
                }
            )
        )

        self.assertEqual(targets[0].profile, "student-autograded")
        self.assertEqual(targets[0].languages, ["python", "sql"])

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

    @patch("publish.run_command")
    def test_push_branch_uses_force_with_lease_only_when_requested(self, mock_run_command) -> None:
        push_branch(self.workspace, "automation/claude-instructions-v1.0.0", {}, force_with_lease=False)
        push_branch(self.workspace, "automation/claude-instructions-v1.0.0", {}, force_with_lease=True)

        first_command = mock_run_command.call_args_list[0].args[0]
        second_command = mock_run_command.call_args_list[1].args[0]
        self.assertNotIn("--force-with-lease", first_command)
        self.assertIn("--force-with-lease", second_command)


if __name__ == "__main__":
    unittest.main()
