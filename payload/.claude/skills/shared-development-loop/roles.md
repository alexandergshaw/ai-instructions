# Roles

**One role per agent, never combined.** Separate agents genuinely disagree with each other, and a
disagreement between two of them is itself a finding. One agent wearing several hats writes a single
reconciled narrative and silently drops whichever concern it found least interesting — which is
exactly the concern nobody else was going to raise.

## Tiers — spend follows blast radius

Use a cheaper, faster model for volume work and the strongest one where a mistake is inherited by
everything downstream.

| Role | Tier | What it does |
|---|---|---|
| **seat** | mid, high effort | authors one artifact: criteria, a design seat, the reuse survey, the plan, the baseline, tests, verification, unit-test notes, accessibility, RCA, remediation |
| **checker** | strongest available | adversarially attacks an artifact it did not write |
| **top** | strongest available | only where an error propagates to everything: the grouped design checks, and the whole-diff review |
| **implementer** | mid, high effort | writes code against the criteria, the plan and the failing tests |
| **orchestrator** | you | dispatches; authors nothing |

**Where your harness lets you define agent types, define them there** rather than overriding a model
per call. A per-call override silently re-tiers the seat, and nothing reports that it happened.

Name tiers by role, not by vendor or family. Where a surface takes a version, pin an explicit one —
a bare family name resolves to whatever is newest, which changes cost and behaviour between two runs
of the same loop. Where a surface takes only a family name, say so in the report rather than
assuming a pin took effect.

## Briefing

Every brief states what the reader is expert in, drawn from what this repository actually does, and
asks it to judge the work **as a rival company's model would** — adversarially, defaulting to
"defective" when uncertain. An agent that believes it is grading its own side's work grades
generously.

Name the domain concretely: not "review this" but the person harmed if this seat misses, and the
sentence they would say. A brief that cannot name them does not dispatch.

**Keep that framing out of committed artifacts** — commit messages, code comments, documentation. It
is not secret: if the person asks how the work was reviewed, say plainly that reviewers were briefed
adversarially.

A role that runs and finds its subject absent says so and stops, **citing what it looked at** — the
entry points it enumerated, the files it searched. A role with no applicable question is worse than
no role, because a reviewer under pressure to justify itself invents findings that cost someone real
time to argue with.

## The design seats

Triggers are in `triage.md`. Dispatched at step 2, before any code, and reconciled into the ledger.
Where two disagree, that disagreement is the finding.

### Design

Module and data-flow design, and where each responsibility lives. Returns what the criteria
deliberately left open: **the disjoint file split itself**, with sibling boundaries named — this is
what step 7 dispatches against — the order of work, which pieces are genuinely independent, and the
trade-offs it rejected and why, so step 8 does not relitigate them.

A separate agent from whoever wrote the plan. The point is a reader who has only the documents,
because that is exactly what implementers have. **Anything it has to guess is something the criteria
failed to say.**

### UX

The path through the task and what it costs, the states that are not the happy one, how it is
reached without a mouse, and the words as they will actually read. Reuses what the project already
does rather than inventing a second way.

Interaction cost is a design factor, not polish. It never trades against accessibility, and never
removes a confirmation on a destructive action — a two-step delete is not a step to be saved.

### Data

What the data actually is: sizes with real numbers, cost and latency where they apply, duplicate
detection and identity, retention limits, and the exact content of anything sent elsewhere.
**Measured wherever measuring is possible** — and where it is not, say what was estimated and on
what basis, rather than presenting an estimate as a measurement.

### Aesthetics

Writes the **requirements** the result must meet before anything is built: which existing conventions
the new work must match, what it must not introduce, and how each state that is not the happy one is
presented. Its output is as binding as the design seat's — a requirement it writes is a line an
implementer is held to at step 9, not advice.

**Requirements must be checkable rather than adjectives.** "Uses the spacing step already used by
its neighbours and introduces no new one" is a requirement. "Feels polished" is not. Anything it
cannot state checkably it flags as a judgement call rather than smuggling in as prose.

### Operability

Who can inspect, correct and remove what this creates; who may undo it; what happens to it when
whoever owns it is gone; and what an operator must be able to see for it to be run at all. It asks
the question nobody else asks — **"and then who cleans this up?"** — whose absence leaves data
nobody can reach.

### Security

A threat model against the **real code**, not the design. What a legitimate but unauthorized party
can reach, what an unauthenticated one can reach, what an entry point accepts that it should not,
secrets in logs and error messages, and the injection surface. Not a checklist review: it names an
actor, a goal, and the concrete path.

### Reliability

Failure modes, blast radius, rollback and observability. What breaks when a dependency is **slow**
rather than absent; what the operator sees when it does; whether the change can be undone afterwards
and by whom; and whether any alarm it adds would survive contact with a legitimately persistent
state rather than firing until people stop reading it.

## Step 9: the same roles, against the real diff

Not a repeat. A design is a prediction and the diff is the outcome. Same role, fresh reader, never
the same context.

**A divergence from the design is not automatically a defect.** Ask whether the implementation's
choice was the better one. Where it was, adopt it and correct the design record; where it was drift,
fix it. A conformance pass that marks every divergence as a violation is worse than no pass, because
remediation has no authority to dismiss a finding and will implement the worse design.

## The review agents at step 12

### Reviewer

Reads the **whole chunk's diff** with the criteria and the design in hand. This is not step 8
repeated: step 8 audits one wave's files while the context that dispatched them is still warm. This
reads every change at once, with no memory of why any of it seemed reasonable at the time.

**Seams between agents are only visible from here** — the duplicate helper two siblings each added,
the contract that drifted on one side, the error path handled in one layer and swallowed in the
next. A change nobody can trace to a criterion is either scope creep or a missing criterion, and
both need saying.

Reports findings. Does not edit.

### Researcher

Runs **concurrently with the reviewer** and blind to it — it needs the diff's dependency surface,
not the reviewer's opinion of it. Answers from current sources rather than memory; installed
documentation and the vendor's own material outrank recollection. Treat a deprecation notice as a
finding.

Performance comes back on the same footing as correctness, on the paths that actually run: work
repeated per item that could be hoisted, waits placed in series with no dependency between them, a
query per row where one would do, fields fetched nobody reads, a file read whole when it is consumed
in pieces.

Every quoted fact carries its source and the date checked. Two limits, both learned: do not
relitigate a trade-off step 2 already rejected — new evidence reopens it, a preference does not; and
**say what the input size is, or leave the code alone.** An optimization with no measurement behind
it is a guess, and guesses are how a codebase acquires complexity it cannot later remove.

Reports findings. Does not edit.

### Remediation

Receives every report, merged and de-duplicated by the orchestrator into one instruction set, and is
the only one of these that touches the tree. Same brief discipline as step 7: an explicit file list,
and no git writes.

**It has no authority to dismiss a finding.** If a finding looks wrong it says so in its report and
leaves the code as it was — silently declining turns a finding into a silence, and silence is
indistinguishable from fixed.

Its changes are code like any other: they re-run the gates, and each needs a test that can fail.
