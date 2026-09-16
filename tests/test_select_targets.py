"""Which repositories a single publish run reaches.

This decides where automation writes and how wide the App token's scope is, so the failure
modes here are loud by design: an unmatched name aborts before anything is cloned, and an
empty selection is never emitted -- an empty `repositories` value, with `owner` set, grants
the token access to every repository in the installation.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from select_targets import (  # noqa: E402
    SelectionError,
    parse_requested,
    repository_names,
    select_targets,
)

FLEET = {
    "targets": [
        {"repo": "owner/instructions-sync-test", "enabled": True},
        {"repo": "owner/python", "enabled": True},
        {"repo": "owner/python-course", "enabled": True},
        {"repo": "owner/retired", "enabled": False},
    ]
}


def names(selected):
    return [t["repo"] for t in selected]


class ParseTests(unittest.TestCase):
    def test_blank_means_every_enabled_target(self) -> None:
        for raw in ("", "   ", None):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_requested(raw))

    def test_separators_and_whitespace_are_tolerated(self) -> None:
        self.assertEqual(parse_requested(" a , b,\nc "), ["a", "b", "c"])

    def test_a_trailing_comma_does_not_create_an_empty_entry(self) -> None:
        self.assertEqual(parse_requested("a, b,"), ["a", "b"])

    def test_a_separators_only_value_is_not_silently_treated_as_blank(self) -> None:
        """',' is a typo, not a request for the whole fleet."""
        with self.assertRaisesRegex(SelectionError, "named no repository"):
            parse_requested(",")


class SelectionTests(unittest.TestCase):
    def test_no_request_selects_every_enabled_target(self) -> None:
        selected = select_targets(FLEET, None)
        self.assertEqual(
            names(selected), ["owner/instructions-sync-test", "owner/python", "owner/python-course"]
        )

    def test_a_subset_selects_exactly_that_subset(self) -> None:
        selected = select_targets(FLEET, ["python", "instructions-sync-test"])
        self.assertEqual(names(selected), ["owner/instructions-sync-test", "owner/python"])

    def test_a_fully_qualified_name_is_accepted(self) -> None:
        self.assertEqual(names(select_targets(FLEET, ["owner/python"])), ["owner/python"])

    def test_matching_is_exact_and_never_a_prefix(self) -> None:
        """`python` must not drag in `python-course`. The real fleet has this collision."""
        self.assertEqual(names(select_targets(FLEET, ["python"])), ["owner/python"])

    def test_an_unknown_name_aborts_and_names_the_value(self) -> None:
        with self.assertRaisesRegex(SelectionError, "no-such-repo"):
            select_targets(FLEET, ["no-such-repo"])

    def test_a_disabled_target_cannot_be_reached_by_naming_it(self) -> None:
        """Scoping narrows. `enabled` stays the outer gate."""
        with self.assertRaisesRegex(SelectionError, "not enabled"):
            select_targets(FLEET, ["retired"])

    def test_an_ambiguous_bare_name_is_refused_rather_than_guessed(self) -> None:
        two_owners = {
            "targets": [
                {"repo": "a/course", "enabled": True},
                {"repo": "b/course", "enabled": True},
            ]
        }
        with self.assertRaisesRegex(SelectionError, "ambiguous"):
            select_targets(two_owners, ["course"])

    def test_matching_is_case_insensitive(self) -> None:
        self.assertEqual(names(select_targets(FLEET, ["Python-Course"])), ["owner/python-course"])

    def test_a_duplicate_request_selects_the_target_once(self) -> None:
        self.assertEqual(names(select_targets(FLEET, ["python", "owner/python"])), ["owner/python"])

    def test_an_empty_enabled_set_is_an_error_not_an_empty_selection(self) -> None:
        """An empty `repositories` value grants the token the whole installation."""
        with self.assertRaisesRegex(SelectionError, "no enabled targets"):
            select_targets({"targets": [{"repo": "owner/x", "enabled": False}]}, None)


class RepositoryNameTests(unittest.TestCase):
    def test_names_are_bare_and_carry_no_owner(self) -> None:
        selected = select_targets(FLEET, ["python"])
        rendered = repository_names(selected)
        self.assertEqual(rendered, ["python"])
        self.assertNotIn("/", "".join(rendered))

    def test_the_rendered_list_is_never_empty(self) -> None:
        with self.assertRaises(SelectionError):
            repository_names([])


class CliTests(unittest.TestCase):
    def test_the_cli_emits_one_output_line_and_cannot_inject_another(self) -> None:
        import select_targets as module

        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "targets.json"
            config.write_text(json.dumps(FLEET), encoding="utf-8")
            line = module.render_output(config, "python")

        self.assertEqual(line, "repositories=python")
        self.assertEqual(line.count("\n"), 0)

    def test_a_newline_in_the_request_is_refused(self) -> None:
        """A value reaching GITHUB_OUTPUT must not be able to append a second assignment."""
        import select_targets as module

        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "targets.json"
            config.write_text(json.dumps(FLEET), encoding="utf-8")
            with self.assertRaises(SelectionError):
                module.render_output(config, "python\nrepositories=everything")


if __name__ == "__main__":
    unittest.main()
