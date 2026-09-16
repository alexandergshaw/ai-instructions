"""Delivery guarantees for the shipped payload.

These assert what every downstream repository actually receives, against the real payload and
the real profiles -- not against a synthetic fixture. The distinction matters: a profile that
selects nothing, or a delivered file whose cross-references point at files that profile does
not deliver, is invisible to a fixture-based test.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sync_payload import REQUIRED_PAYLOAD_PATHS, get_payload_files  # noqa: E402

PAYLOAD_ROOT = ROOT / "payload"
PROFILES_PATH = ROOT / "config" / "profiles.json"

# A reference inside a delivered file that points at another distributed file.
CLAUDE_PATH_PATTERN = re.compile(r"`(\.claude/[A-Za-z0-9_./-]+)`")


def _profiles() -> dict[str, tuple[str, ...]]:
    data = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    return {name: tuple(prefixes) for name, prefixes in data["profiles"].items()}


def _delivered(selection: tuple[str, ...] | None) -> list[str]:
    return [path.as_posix() for path in get_payload_files(PAYLOAD_ROOT, selection)]


class DeliveryTests(unittest.TestCase):
    def selections(self) -> dict[str, tuple[str, ...] | None]:
        """Every way a target can be configured, including the no-profile default."""
        selections: dict[str, tuple[str, ...] | None] = {"(no profile)": None}
        selections.update(_profiles())
        return selections

    def test_every_selection_delivers_the_required_paths(self) -> None:
        """A profile cannot exclude what REQUIRED_PAYLOAD_PATHS names."""
        for label, selection in self.selections().items():
            delivered = _delivered(selection)
            for required in REQUIRED_PAYLOAD_PATHS:
                with self.subTest(selection=label, required=required):
                    matched = [
                        path
                        for path in delivered
                        if path == required
                        or (required.endswith("/") and path.startswith(required))
                    ]
                    self.assertTrue(matched, f"{label} delivers nothing for {required}")

    def test_every_selection_delivers_the_development_loop(self) -> None:
        for label, selection in self.selections().items():
            with self.subTest(selection=label):
                delivered = _delivered(selection)
                self.assertTrue(
                    any("shared-development-loop" in path for path in delivered),
                    f"{label} does not deliver the development loop",
                )

    def test_no_delivered_file_references_a_file_its_profile_does_not_deliver(self) -> None:
        """A cross-reference to an undelivered file is a broken instruction downstream."""
        for label, selection in self.selections().items():
            delivered = _delivered(selection)
            delivered_set = set(delivered)
            for relative_path in delivered:
                text = (PAYLOAD_ROOT / relative_path).read_text(encoding="utf-8")
                for reference in CLAUDE_PATH_PATTERN.findall(text):
                    with self.subTest(selection=label, source=relative_path, ref=reference):
                        self.assertIn(
                            reference,
                            delivered_set,
                            f"{label}: {relative_path} references undelivered {reference}",
                        )

    def test_the_reference_check_catches_a_bogus_path(self) -> None:
        """Control for the test above: the instrument must fire on a known-bad reference."""
        delivered_set = {".claude/shared/core/engineering.md"}
        text = "See `.claude/shared/core/does-not-exist.md` for details."

        found = CLAUDE_PATH_PATTERN.findall(text)

        self.assertEqual(found, [".claude/shared/core/does-not-exist.md"])
        self.assertNotIn(found[0], delivered_set)

    def test_the_reference_check_finds_real_references(self) -> None:
        """Control: the pattern must hit the references that genuinely exist in the payload."""
        hits = 0
        for relative_path in _delivered(None):
            text = (PAYLOAD_ROOT / relative_path).read_text(encoding="utf-8")
            hits += len(CLAUDE_PATH_PATTERN.findall(text))

        self.assertGreater(hits, 0, "the reference pattern matched nothing at all")


class StepCitationTests(unittest.TestCase):
    """Every 'stage N' / 'step N' in the payload must resolve to a heading that exists."""

    CITATION = re.compile(r"\b(?:stage|step)\s+(\d+[a-z]?)\b", re.IGNORECASE)
    HEADING = re.compile(r"^#{1,6}\s+(\d+[a-z]?)\.", re.MULTILINE)

    def _headings(self, directory: Path) -> set[str]:
        headings: set[str] = set()
        for path in directory.rglob("*.md"):
            headings.update(self.HEADING.findall(path.read_text(encoding="utf-8")))
        return headings

    def test_no_step_citation_dangles(self) -> None:
        skill_dir = PAYLOAD_ROOT / ".claude/skills/shared-development-loop"
        headings = self._headings(skill_dir)
        self.assertTrue(headings, "no numbered headings found to resolve against")

        for path in sorted(PAYLOAD_ROOT.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            for cited in self.CITATION.findall(text):
                with self.subTest(source=path.relative_to(PAYLOAD_ROOT).as_posix(), cited=cited):
                    self.assertIn(cited.lower(), {h.lower() for h in headings})

    def test_the_citation_check_catches_a_bogus_reference(self) -> None:
        """Control: the instrument must fire on a citation that resolves to nothing."""
        self.assertEqual(self.CITATION.findall("this is handled at stage 99."), ["99"])
        self.assertEqual(self.HEADING.findall("## 4. Seven pre-code passes"), ["4"])


if __name__ == "__main__":
    unittest.main()
