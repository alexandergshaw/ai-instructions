---
name: shared-development-loop
description: The staged development process for this repository. Use when a change spans three or more files, or when several agents will work on it concurrently. Not for a change confined to one file, a typo, a question, or anything a single reader can verify by reading the diff. Assumes the agent can dispatch subagents; a full run costs up to eighteen of them, so say what it will cost before starting. Covers acceptance criteria that land red, seat triage with a regex backstop, dispatch on disjoint file sets, checks that carry controls, a sabotage pass over units, and a regression pass with refuters. Companion files - roles.md, triage.md, checks.md, ledger.md, traps.md, retrospective.md, subagent-execution.md - are in this directory. It ends with a retrospective that changes nothing and reports on the loop itself.
---

# Development Loop

It exists to solve one problem: **a model that writes code and then judges its own code will pass
it.** Everything here is machinery around that single fact.

The **Invariants** below hold for every step of this loop. The rules that hold for any change at
all, whether or not this loop runs, are in `.claude/shared/core/engineering.md` and the
`shared-agent-floor` skill.

## The floor

The `shared-agent-floor` skill bounds what may be done without being asked. Nothing in this loop
lifts any of it. In particular, no step here authorizes committing, pushing, opening a pull request,
merging, or starting a further piece of work.

**The loop's queue contains only work the person asked for in this conversation.** Chunking that
work is yours to decide; chunking does not create entries. Completing a chunk authorizes nothing
beyond it.

## Invariants

**The author and the checker of any artifact are never the same agent.** Not just code — criteria,
designs, plans, tests, bug reports, adjudications and regression results are each written by one
agent and attacked by a different, fresh one. Whoever orchestrates authors no artifact a checker
will later read as a seat's work: it chunks, briefs, dispatches, reconciles on evidence, records
status against rows a seat wrote, and reports. Where it must write the adjudication itself, or hold
the ledger because the repository keeps no working documents, **that writing is checked by a fresh
agent like any other artifact.** Catching yourself *producing* an artifact
instead of *routing* one is the signal to spawn the seat, and **"it's faster to just do it myself"
is precisely that signal.**

**Tests land red before the code, for the right reason.** A criteria round whose every criterion
already passes is the exact defect this process exists to prevent. State which are red and which are
green-and-regression-guarding. The method for proving a test can fail, and the catalogue of shapes
that cannot, are in `.claude/shared/testing/general.md`.

**A landed test is never weakened or edited to make an implementation pass.** An implementer that
believes a test is wrong stops and reports — the conflict between a criterion and a test is how
defective criteria surface.

**A check without a control is not a check.** See `checks.md`.

**Every quantity names its instrument** — a command, a test title, or `file:line`. A number without
one rots silently. A criterion satisfied by a comment containing the right words measures nothing,
and **a failed instrument is invalid, not zero**: if the apparatus broke you have no reading, not a
reading of zero. Say which, in the output.

**Never claim "nothing does X" from one search.** Every absence claim needs a canary — a pattern
that *must* hit, run on the same instrument. Cite code, never the comment above it.

**Say what you had to guess.** Every guess is a line the criteria failed to write.

**No agent running this loop performs a git write** — not `stash`, `checkout`, `restore`, `reset`,
`add`, `commit` or `push` — whether or not other agents are working in the tree. A permission
configuration that allows one is not a request to run it. Read-only git is fine and useful.

**When a mechanism's dependency is absent, skip it and say so.** Several steps below assume
something a repository may not have — a regression corpus, a linter, a build, a durable log. Where
it is absent: report that, create no files, invent no thresholds, and do not report the step as
passed.

## 0. Before anything else

**0a. Compare** the request against what is already done or in flight — history, any record the
repository keeps, running agents. A surprising share of requests are already built or already
contradicted by something in the tree. If so, say it and reframe the work, in the same turn.

**0b. Re-chunk the whole queue** when a request lands; never append to a flat list. Priority:
file-set disjointness, then unblockers, then same-evidence items together, then each chunk
independently completable, and **never chunk around the gates**.

**0c. Dispatch disjoint work concurrently** — within the chunk the person asked for, never a later
one, which 0d holds. Disjointness has two halves and both must hold — see
`subagent-execution.md`, which also carries the wave cap and the third check over existing callers.

**0c-bis. When a chunk completes**, re-check every unstarted chunk's artifacts that name a file it
touched, before their next consumer reads them.

**0d. A new request does not preempt the in-flight chunk.** Research and criteria may run in
parallel; its *code* waits until the current chunk is **complete** — gates passed and handed over.
Completion is what releases the next chunk's code, and starting it still needs a new request.

A correction is not a queued request. If the person says stop, changes the requirement, or says the
work is wrong, that takes effect immediately.

**0e. Seat triage** — which design seats run, decided from the planned change, with the trigger that
fired recorded. See `triage.md`.

## 1. Acceptance criteria

Numbered `AC1`, `AC2`, … so implementers and reviewers can cite them. Every criterion names its
instrument. **At least one must be red on HEAD today, for the right reason.**

Criteria fix what concurrent agents would otherwise each invent differently: exact signatures and
return shapes, exact parameter names sent to anything external, exact error messages where the
wording is load-bearing, and which file owns what. Verified external facts go in with their source
and the date checked, quoted.

**When the change exists to save something — money, time, runs — the first criterion measures the
saving under the gate's own rules, before any criterion designs machinery.** If it comes out near
zero, the person decides scope before another round is spent.

Record them where the repository keeps working documents; if it keeps none, state them in your
report rather than creating a file.

## 2. Design seats

The triggered ones, spawned in one message, reconciled into the ledger, then checked in groups along
the seams. Briefs in `roles.md`; grouping in `checks.md`; the ledger in `ledger.md`.

**Then one seat consolidates them into a single design document** — written where this repository
keeps working documents, or stated in the orchestrator's report where it keeps none, never as a new
file in the tree — in which every cross-seat contract
— formats, protocols, shared constants — is defined **exactly once**. The individual seat artifacts
freeze as rationale, and the plan and tests consume only that document plus the ledger. Two authors
following the same rulings still wrote one contract three different ways: **a seam that lives in two
files is a seam that drifts.**

## 3. Reuse survey

A vetted `| Need | Reuse | Where |` table with paths and line numbers. **Verify each candidate by
reading it and its call sites** — never by name. The call sites are the half people skip and where
the answer usually is. If the survey finds structure a design seat ignored, that seat is revised and
re-checked before the plan consumes it.

## 4. Plan

The plan consumes the ledger. A requirement it cannot realize is a conflict the orchestrator
adjudicates — **never a silent drop**. The plan's checker also re-triages external facts: does the
plan rest on any fact outside the repository not yet confirmed at its primary source? Each is then
confirmed there, folded into the criteria, and the plan re-run until a pass changes nothing.

## 5. Baseline

Only where the area has no existing coverage. Observe the current behaviour in a copy made outside
the repository. **Never restore or check out the tree in order to observe it** — that discards
uncommitted work, and in a repository that pre-approves git commands it does so without asking.
Record what is **not** covered as explicitly as what
is.

Where the repository keeps a regression record, baseline into it. Where it does not, put the
baseline in your report and say so. Do not create a top-level directory for it. In a repository
holding graded or assessed work, no baseline or regression output describes a solution or a grading
gap in a committed file.

## 6. Tests land red

Before any implementation. The test author states, by list, that its reference implementation covers
every planned edit.

The **test checker builds its own reference** from the plan in an isolated copy, runs the mutation
harness with a no-op control, re-observes the baseline, and answers both questions: *can a green
test fail?* and *can a red test pass for the right reason?*

## 7. Code

The implementer is briefed with the criteria by path, the plan, the ledger, the reuse notes, the
failing tests, and an explicit allowed-file list. It never weakens or edits a landed test — it stops
and reports. A landed test changes only through a seat whose brief cites the ruling authorizing it.

A sibling's module reported missing by a type check is reported, never created or inlined.

## 8. Verify

A seat, never the author. Read the diff; run the gates; exercise every criterion; **confirm each new
value at its production call site by hand**; and **rule on every triaged-out seat's trigger against
the built diff** — briefed with the triaged-out *list* only, never the triage rationale, so it rules
fresh. List the external behaviours the diff depends on.

Report the line count of every touched file. Compare against a limit only where the repository
defines one; never invent a threshold. **Never split a file whose path or single-file shape is fixed
by an assignment, an autograder, a submission process, or code that reads it by path** — report the
size instead.

Findings become bug reports → checked, the checker attacking every "trigger does not hold" ruling →
implementer → re-verify, until every criterion passes.

## 9. Design follow-ups

For every seat that ran, plus every seat the verify step forced. **A forced seat has no pre-code
half, so it runs as two agents:** its pre-code seat first, briefed with the criteria and plan but
**not the built diff**, so it cannot endorse the code it is about to judge; then its follow-up.

A divergence from the design is not automatically a defect. Where the implementation's choice was
better, adopt it and correct the record; where it was drift, fix it.

## 10. Unit tests

Notes enumerate a unit for **every source file in the diff** → implementers write them, disjoint
unit sets in parallel, **allowed files: test files only** — and where the only test file available
holds assessed work, such as an assignment's own test file, an autograder, or anything a submission
process reads by path, **do not write into it**: report the units that could not be added and stop → a **sabotage pass over every unit** →
one full-suite run.

The sabotage pass is the load-bearing part, and it runs against a copy, never the working tree — see
`.claude/shared/testing/general.md`, which is canonical for the method. Mutate **one unit at a
time** by exact-string replacement asserting an occurrence count of 1. Include a **no-op control
mutant that must survive**. Read verdicts off the runner's own summary line, not from narration.
**Survivors go back to the implementer as blockers** — a weak test surfaced is the entire point.

## 11. Accessibility

Where the repository renders an interface or generates a document. **It gates the regression — never
start one with known accessibility failures.** A checklist with `file:line` citations: an accessible
name on every control; a role that can carry a label, which a bare generic container cannot;
keyboard reachability of anything interactive or scrollable; focus restored after removal; error
text announced rather than only shown; live regions not flooded by a repeating update.

Where it renders nothing, say so and skip.

## 12. Whole-diff review

The reviewer reads the whole chunk's diff with the criteria and design in hand, concurrently with
the researcher, which is blind to the reviewer's findings. Then the orchestrator adjudicates into
**one** instruction set, **writing down what is deliberately not done and why**; the adjudication is
itself checked; remediation applies it; and a fresh delta review reports every adjudicated item as
**applied / not applied / applied differently**.

**Every later code change, however small, re-enters this as a delta review** before the next
regression run.

## 13. Regression

One pass per group, with the chunk's criteria appended as cases first. Where the repository has no
case corpus, say so and run the tests it does have — do not invent a corpus.

- **a.** An integrity check over the corpus passes; its rows define the expected set. Where the
  repository has no such check, say so, take the corpus rows as the expected set unverified, and
  report this bucket as unrun rather than passed.
- **b.** Every test command in the corpus, collected **by traversal, never a flat glob**, **each
  checked to exist**, in one run. Read the summary line. No agent.
- **c.** Every automatable case executed, all steps.
- **d.** Manual cases → reviewer seats, **grouped by defect class, not by file**.
- **e.** **Every reported failure goes to a refuter before it counts** — and so does every failure
  the runner itself dismissed as "could not reproduce" or "stale environment", before it is dropped.

**The result is a work product, not a verdict.** Buckets c–d get a fresh checker under the sampling
rule in `checks.md`. Report executed versus expected per bucket, every unrun case by ID, and the
automated and manual sets **separately — never as one coverage figure**.

## 14. RCA

For anything that got through: causal chain with `file:line` and a prescribed fix → implementer →
delta review → regression re-run. Loop until the gates are green on code that has been reviewed in
the state it was run in.

## 15. Hand over

Report the gates with their real numbers and their limits: what was never run, never rendered, never
observed. A report listing only successes is a trap for the next session.

Then stop. Committing, pushing, opening a pull request and merging are the person's, per the floor.

## 16. Retrospective

After the loop completes, once. **It changes nothing** — no file is edited and no finding is acted
on. It produces one peer-verified report about **the loop itself**: where the process earned its
cost, where it did not, which rules could not be followed here, and which were ambiguous.

The report is written for someone who maintains the loop centrally and **cannot see this repository
or this session**, so every claim cites a step, a seat, a round, a quoted rule or real output, and
every proposed change quotes the text it would replace. It is checked by a fresh agent that did not
write it and did not run the loop.

Format, classification rules and the checker's brief are in `retrospective.md`.
