from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate import validate_payload, validate_targets_config  # noqa: E402


class ValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        (self.repo_root / "config").mkdir()
        (self.repo_root / "payload/.claude/shared/core").mkdir(parents=True)
        (self.repo_root / "payload/.claude/skills/shared-example").mkdir(parents=True)
        (self.repo_root / "payload/.claude/shared/core/engineering.md").write_text("content", encoding="utf-8")
        (self.repo_root / "payload/.claude/skills/shared-example/SKILL.md").write_text("content", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_targets(self, payload: object) -> Path:
        path = self.repo_root / "config/targets.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_valid_target_configuration(self) -> None:
        errors = validate_targets_config(
            self.write_targets({"targets": [{"repo": "owner/repository", "enabled": True}]})
        )
        self.assertEqual(errors, [])

    def test_malformed_repo_name_is_rejected(self) -> None:
        errors = validate_targets_config(
            self.write_targets({"targets": [{"repo": "not a repo", "enabled": True}]})
        )
        self.assertTrue(any("owner/repository" in error for error in errors))

    def test_duplicate_repo_names_are_rejected(self) -> None:
        errors = validate_targets_config(
            self.write_targets(
                {"targets": [{"repo": "owner/repository", "enabled": True}, {"repo": "owner/repository", "enabled": False}]}
            )
        )
        self.assertTrue(any("Duplicate repository entry" in error for error in errors))

    def test_invalid_enabled_value_is_rejected(self) -> None:
        errors = validate_targets_config(
            self.write_targets({"targets": [{"repo": "owner/repository", "enabled": "yes"}]})
        )
        self.assertTrue(any("boolean" in error for error in errors))

    def test_missing_payload_is_rejected(self) -> None:
        errors = validate_payload(self.repo_root / "missing-payload")
        self.assertTrue(any("Missing payload directory" in error for error in errors))

    def test_root_claude_md_in_payload_is_forbidden(self) -> None:
        (self.repo_root / "payload/CLAUDE.md").write_text("forbidden", encoding="utf-8")

        errors = validate_payload(self.repo_root / "payload")

        self.assertTrue(any("root CLAUDE.md" in error for error in errors))

    def test_empty_markdown_file_is_rejected(self) -> None:
        (self.repo_root / "payload/.claude/shared/core/empty.md").write_text("\n", encoding="utf-8")

        errors = validate_payload(self.repo_root / "payload")

        self.assertTrue(any("non-empty" in error for error in errors))

    def test_incorrectly_named_skill_is_rejected(self) -> None:
        wrong_skill = self.repo_root / "payload/.claude/skills/not-shared"
        wrong_skill.mkdir(parents=True)
        (wrong_skill / "SKILL.md").write_text("content", encoding="utf-8")

        errors = validate_payload(self.repo_root / "payload")

        self.assertTrue(any("begin with 'shared-'" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
