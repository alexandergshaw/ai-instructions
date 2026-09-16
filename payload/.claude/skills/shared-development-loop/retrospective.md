# The retrospective

Runs once, after the loop completes. **It changes nothing** — no file is edited, no fix is applied,
no finding is acted on. Its only output is a report about **the loop itself**, written to be read by
someone who maintains the loop centrally and who cannot see this repository or this session.

That last constraint decides almost everything below. The reader has no access to the work, the
agents, the diff or the conversation. A claim they cannot check from the report alone is not usable,
and an observation without enough context to act on is noise they have to chase.

## What it is not

- **Not a review of the code.** The code was reviewed at step 12. This examines the process.
- **Not a to-do list for this repository.** A defect in this repository's setup — no linter, no
  corpus, a confusing file layout — belongs in your report to the person here, not in this one,
  unless the loop handled it badly.
- **Not a place to re-litigate findings.** A finding you disagreed with is worth reporting only if
  the *rule that produced it* is the problem.

## Separate three things, because only one is actionable centrally

Every observation is classified, and the classification is part of the report:

- **Loop defect** — the instruction is wrong, ambiguous, impossible here, or costs more than it
  returns. Actionable centrally. This is what the report is for.
- **Application defect** — the instruction was fine and was followed badly, by whoever ran it.
  Report it, briefly, so the central reader can tell the difference — a rule that is *repeatedly*
  applied badly is usually a rule that is unclear.
- **Repository defect** — this repository lacked something the loop reasonably expects. Report only
  if the loop's degradation path handled it badly.

## Evidence

**Every claim cites something.** A step number, a seat, a round, a finding, a quoted rule, or real
command output. "Stage 4 worked well" is worthless to the reader; "the security seat's trigger fired
on a change with no network boundary, and its report said *no applicable surface*, which cost one
dispatch" is actionable.

**Quote the rule you are commenting on, verbatim, with its file and heading**, so the central reader
can find it without guessing. A proposed change that does not quote what it would replace cannot be
applied.

**Report what the loop caught, not only what it cost.** A retrospective listing only friction argues
for deleting the loop. Name each finding the process surfaced, which seat found it, at which step,
and what it would have cost had it shipped. That half is the evidence the machinery earned its
price, and it is the half that is hardest to reconstruct later.

## Cost

Report it plainly: agents dispatched, per step; rounds per artifact; which artifacts needed a second
or third round and on what. Where the loop was skipped, say which parts and why.

## Nothing that identifies a person or reveals assessed work

In a repository holding graded or assessed material, the report describes the process, never the
solution. No student's code, no submitted answer, no grading gap, and no name.

## The report

```text
## Retrospective — <what the change was, one line>

**Repository shape.** Language, rough size, and what the loop had to work with: tests, a regression
record, a linter, a build, CI — and what was absent.

**Steps run.** Each step: ran / skipped, with the trigger or the reason. Name every seat dispatched.

**What the loop caught.** Per finding: seat, step, what it found, and what it would have cost if it
had shipped.

**What cost more than it returned.** Per instance: the step, what was spent, what came back.

**Rules that could not be followed.** Quote the rule with its file and heading. Say what blocked it
and what you did instead.

**Rules that were ambiguous.** Quote the rule. Give both readings. Say which you took and why.

**Rounds.** Per artifact: how many, and what the last round changed. Note anywhere termination was
reached.

**Proposed loop changes.** Each one: file, heading, the text today, the proposed replacement, and
the observation above that motivates it. Classified loop / application / repository.

**Limits of this retrospective.** What you could not observe, what you are inferring, and which
proposed changes rest on a single occurrence.
```

A proposal resting on one occurrence is still worth reporting — say so, rather than dropping it or
dressing it as a pattern.

## It is peer-verified

The retrospective is an artifact, so it is checked like any other: by a fresh agent that did not
write it and did not run the loop it describes.

That checker's brief is specific, because the usual failure here is flattery:

- **Attack every "this went well".** Which are supported by a named finding, and which are an
  impression? An unsupported success claim is the most likely defect in this artifact, because
  nothing in the session pushes back on it.
- **Attack the classification.** Which "loop defects" are actually application defects — the rule
  was clear and was not followed — or repository defects wearing a loop defect's clothes? Misfiled
  observations send the central maintainer to change a rule that was working.
- **Verify every quoted rule actually says what the report claims**, by opening the file. A
  misquoted rule produces a change to text that was never the problem.
- **Check the cost figures against the record**, not against the narrative.
- **Find what the report omits.** A step that silently did not run, a seat that returned nothing and
  was not mentioned, a round that is missing from the count.

The checker's findings go back to the author, and the corrected report is what gets handed over.
Where author and checker still disagree, **both positions appear in the report** with their
evidence — the central reader can adjudicate, and a suppressed disagreement is exactly the signal
they most need.
