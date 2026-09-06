---
name: shared-development-loop
description: The full multi-agent development loop - acceptance criteria first, pre-code review passes gated by trigger, dispatch on disjoint file sets, follow-up passes against the real diff, a review before regression, and a regression pass. Use when a change spans three or more files, or when several agents will work on it concurrently. Not for a change confined to one file, a typo, a question, or anything a single reader can verify by reading the diff. Assumes the agent can dispatch subagents; a full run costs up to eighteen of them, so say what it will cost before starting. The always-on principles are in .claude/shared/core/development-loop.md.
---

# Development Loop

Thirteen numbered stages, 0 through 12, plus two follow-ups (8b and 9b). It ends
when the work lands.

The principles this procedure applies — author is never checker, never combine
two roles in one agent, and the non-negotiables — are in
`.claude/shared/core/development-loop.md`. Read that first. Role briefs are in
`roles.md`. If the agent running this loop can dispatch subagents,
`subagent-execution.md` carries the mechanics and the brief template.

## 0. Before anything else

**0a. Compare the request against what is already done, queued, or in flight.**
Check history, any record of past changes the repository keeps, and any running
work. A surprising share of requests are already built, already surveyed, or
already contradicted by something in the tree, and noticing that before
dispatching anyone is the most valuable thing a coordinator does. If a request
turns out to already exist, say so and reframe the work as fixing why it looks
absent, in the same turn.

**0b. Re-chunk the whole queue when a request lands mid-session.** Do not append
it. Re-plan, in this priority order:

1. **File-set disjointness**, proven against real file sets rather than guessed
   from names. Two chunks that both edit one file are one chunk.
2. **Unblockers first** — anything other chunks are coded against.
3. **Same-evidence items together** — work needing the same survey or the same
   measurement should not pay for it twice.
4. **Each chunk independently completable** — a chunk that cannot land alone is
   mis-drawn.
5. **Never chunk around the gates.** A split that exists only to avoid a review
   or a regression pass is the wrong split.

**0c. Dispatch disjoint work concurrently** where the agent can. Prove
disjointness against the real file list before dispatch, and check the returning
wave against the working tree.

**0d. A new request does not preempt the in-flight chunk's code.** Research and
specification for the new thing start immediately and in parallel; its *code*
waits. Interleaving two chunks' code in one working tree is how a regression
pass stops meaning anything.

This does not apply to a correction. If the person you are working with says to
stop, changes the requirement, or says the current work is wrong, that takes
effect immediately — it is not a queued request.

**0e. What does not need asking.** Dispatching disjoint concurrent agents, and
choosing how to chunk the work, are the coordinator's to decide.

Nothing else is. Committing, pushing, opening or merging a pull request, and
starting a further unit of work all sit behind the floor in
`.claude/shared/core/development-loop.md`, which this loop does not lift.

## 1. Write the acceptance criteria first

Before any code, numbered `AC1`, `AC2`, … so they can be cited. Record them
wherever this repository keeps working documents; if it keeps none, state them in
your report rather than creating a file for them. See the core rules for what a
criterion must fix.

Verified external facts go in with their source and date, quoted, so nobody
re-derives them from memory and gets them subtly wrong.

## 2. Reuse survey

Read the codebase before writing the implementation sections, and record a
vetted table: `| Need | Reuse | Where |`, with file paths and line numbers.

**Verify each candidate by reading it and its call sites.** The call sites are
the half people skip, and they are where the answer usually is. Failures this
prevents: acceptance criteria naming a type that does not exist, and citing a
line number from a different file. Both compile. Both would ship.

## 3. Plan, research, revise until stable

Where the work touches an external interface or an unfamiliar standard, verify
the details **before** hand-off. Guessing a parameter name and letting several
agents build on it wastes the whole wave. Fold what you learn back into the
acceptance criteria and re-read them. Stop when a pass changes no acceptance
criterion, no file assignment and no external fact.

## 4. Seven pre-code passes

Architect, UX, data engineer, aesthetics, admin capability, cybersecurity, site
reliability. These are **candidates**, not a fixed set: each carries a trigger in
`roles.md`, and the ones whose triggers fire run before any code, one role per
agent, concurrently where the agent can dispatch.

**Evaluate every trigger and record the result** — which roles ran, which did not,
and why — alongside the acceptance criteria. A coordinator deciding which checks
of its own work get to exist is the core principle inverted, so that decision is
written down where someone else can dispute it.

**A change confined to one file, with no stored data, no interface and no input
from elsewhere, fires no pre-code pass.**

They are independent, they read the same documents, and they find different
classes of problem. Running them in sequence wastes a round trip and lets the
first one's framing contaminate the others.

**A pass that runs and finds its subject absent reports that and stops** — but it
cites what it looked at: the entry points it enumerated, the files it searched,
the command it ran. An assertion without evidence is not a finding, and that
holds for "there is nothing here" exactly as it holds for a defect. A pass with
no applicable question is worse than no pass, because inventing one to look
diligent costs a real reviewer real time.

Reconcile the passes that did apply into the acceptance criteria before planning
goes further. **Where two of them disagree, that disagreement is the finding.**

The architect's output includes the disjoint file split, which is what stage 6
dispatches against. If the architecture contradicts the acceptance criteria, the
criteria are wrong and get fixed before anyone writes code.

## 5. Baseline the area before hand-off

Record what the area does *now*, before changing it, so a later green suite is
not mistaken for coverage that predates it. Note explicitly what is **not**
covered.

Where this repository keeps a regression or change record, baseline into it.
Where it does not, put the baseline in your report to the person you are working
with — not in a new file, and not in a commit message — and say the repository
keeps no such record. **Do not create a new top-level directory for
this.** If a durable log is wanted and the repository has nowhere for it,
`.claude/regression-log.md` is the place to propose — and proposing is as far as
it goes without being asked.

In a repository that holds graded or assessed work, no stage 5 or stage 11
output describes a solution or a grading gap in a committed file.

## 6. Dispatch on disjoint file sets

Every agent gets an explicit allow-list and an explicit statement of which files
belong to its siblings. Each brief carries the acceptance criteria to be read in
full first, its exact assigned files and a refusal to touch anything else, the
existing files to read first for idioms, and the verification commands to run
before reporting.

The rules that are not negotiable in any brief are in `subagent-execution.md`.

A sibling's module reported missing by a type check is reported, never created
or inlined.

## 7. Check every wave against the working tree

Compare the tree against the assignments before trusting a single report.
Spot-check the claims: if an agent says it reused an existing helper, grep for
it.

## 8. Verify: audit, then fix what the audit finds

Read what landed. The audit looks for what tests cannot:

- **Reachability** — is the code wired in, are its inputs threaded, can the
  entry point actually reach it?
- **File size**, where this repository defines a limit — in a linter
  configuration, a style guide, or its own instructions. Count the lines of
  every touched file and report the numbers; the limit is audited, not assumed.
  Report the counts unconditionally; compare them against a limit only where the
  repository defines one, and never invent a threshold. **Never split a file whose name or single-file shape is
  fixed by an assignment, an autograder, or a route that reads it by path** —
  report the size instead.
- **Whether an error's reason survives.**

Findings are fixed directly, and the acceptance criteria are updated to match
any contract change.

## 8b. Follow-up passes against the real diff

The same roles that applied at stage 4, run again against what was actually
built. **A design is a prediction, and the diff is the outcome.** This is where
you learn that the split held but the contracts are unstable, that the flow is
right but an entry point is unreachable, or that the measured cost is nothing
like the estimate.

Same role, fresh reader, never the same context. The aesthetics follow-up is
specifically a conformance check against the requirements it wrote at stage 4.

## 9. Tests, and they must be able to fail

Prove every test can fail, by the method in
`.claude/shared/testing/general.md`, which also holds the catalogue of test
shapes that cannot fail. Pin the fact and the ordering, not the phrasing, unless
the phrasing is itself the requirement. Fixtures must match the shape the code
actually emits.

## 9b. Accessibility gets its own pass

Where this repository renders an interface. Deliberately not folded into the
general review, because it is what a general reviewer skips when the diff is
large, and because automated suites in most repositories check none of it.

A checklist with file-and-line citations: an accessible name on every control; a
role that can actually carry a label, which a bare generic container cannot;
keyboard reachability of anything interactive or scrollable; a disabled-looking
control left focusable where focus must survive; focus restored after something
is removed; error text announced rather than only shown; and live regions not
flooded by a repeating update.

Where the repository renders nothing, say so and skip.

## 10. Review, research, aesthetics and repair — separate agents

Before the regression pass. The reviewer, researcher and fixer always run once
code exists; the aesthetics reviewer runs when its stage 4 counterpart did.
Separate contexts, never one agent wearing several hats:
an agent that found a problem is a poor judge of whether its own fix is
sufficient, and an agent that wrote a fix will not report that the fix was
unnecessary. Briefs in `roles.md`.

The review agents run **concurrently** and report findings; none of them edits.
The fixer receives every report, merged and de-duplicated, and is the only one
that touches the tree.

The reviewer then re-reads the fix diff and confirms each finding is actually
closed. A fix that touched anything outside the reported findings goes round every review
agent again in full.

Findings are closed before regression starts. Reviewing afterwards would only
prove the review was too late to matter.

**The loop-back rule:** if the regression pass causes **any** code to change — a
fix, a revert, a one-line adjustment — return to this stage and run it again
before re-running regression. No regression result counts unless the code it ran
against has been through this stage. A fix written under the pressure of a red
regression is exactly the change most likely to break something else quietly.

**Stop after the second cycle** and raise it rather than starting a third. If two
rounds of fix-and-review have not settled it, the problem is upstream —
usually the acceptance criteria — and the fix is to return there rather than to
keep patching the diff.

## 11. Regression pass, batched per group

A finished item waits until its group is complete. Each group gets **one**
regression pass — never per-item, never several groups rolled together.

Failures get root-cause notes and a fix, and the fix goes back through stage 10
before regression runs again. Repeat until green on code that has been reviewed
in the state it was run in.

Then record the group's outcome where stage 5 put its baseline, including the
**limits**: what was never run, never rendered, never observed. A record that
lists only successes is a trap for the next session.

## 12. Land the work

Hand the work off the way this repository says to. If its instructions do not
say, ask rather than assuming.
