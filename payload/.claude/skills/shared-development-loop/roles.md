# Role Briefs

The peer roles the development loop dispatches: seven candidates before code, four
after. Stage 9b's accessibility pass is briefed inline in `SKILL.md`.
**One role per agent, never combined.**

Each pre-code role, and the aesthetics reviewer, carries an **applies when** line.
A role whose trigger does not fire is not run, and that evaluation is recorded.
The reviewer, researcher and fixer carry no trigger — they always run once code
exists.

A role that runs and finds its subject absent says so and stops, citing what it
looked at: the entry points it enumerated, the files it searched. A role with no
applicable question is worse than no role, because a reviewer under pressure to
justify itself invents findings that cost someone real time to argue with.

Every brief states what the reader is an expert in, drawn from the domain this
repository actually works in, and asks it to judge the work as an outside
reviewer who was not present for the reasoning and cannot ask. An agent
reviewing what it understands to be its own side's work grades generously.

**Keep that framing out of committed artifacts** — commit messages, code comments,
documentation. It is not secret: if the person you are working with asks how the
work was reviewed, say plainly that reviewers were briefed adversarially.

## The seven pre-code passes (stage 4)

Dispatched before any code and reconciled into the acceptance criteria
afterwards. Where two disagree, that disagreement is the finding.

### 4a. Architect

*Applies when: the change touches more than one file.*

Module and data-flow design, and where each new responsibility lives. Returns
what the acceptance criteria deliberately left open:

- **The disjoint file split itself**, with sibling boundaries named. This is
  what stage 6 dispatches against.
- The order of work, and which pieces are genuinely independent.
- The trade-offs it rejected and why, so stage 8 does not relitigate them.

A separate agent from the one that wrote the plan. The point is a reader who has
only the documents, because that is exactly what the implementers will have.
**Anything the architect has to guess is something the acceptance criteria
failed to say.**

### 4b. UX

*Applies when: the change adds or alters something a person operates — a screen, a
command-line interface, a prompt, a flow they must complete.*

The path through the task and what it costs, the states that are not the happy
one, how it is reached without a mouse, and the words as they will actually
read. Reuses what the project already does rather than inventing a second way.

Interaction cost is a design factor, not polish. It never trades against
accessibility, and it never removes a confirmation on a destructive action — a
two-step delete is not a step to be saved.

### 4c. Data engineer

*Applies when: the change persists data, or sends it across a process or network
boundary.*

What the data actually is: sizes with real numbers, cost and latency where they
apply, duplicate detection and identity, retention limits, and the exact content
of anything sent somewhere else. **Measured wherever measuring is possible** —
and where it is not, say what was estimated and on what basis, rather than
presenting an estimate as a measurement.

### 4d. Aesthetics

*Applies when: the change produces something a person looks at.*

Writes the **requirements** the result must meet before anything is built: which
existing conventions in this project the new work has to match, what it must not
introduce, and how each state that is not the happy one is presented.

Not "make it look better afterwards". Its output is as binding as the
architect's: a requirement it writes is a line an implementer is held to at 8b,
not advice.

**Requirements must be checkable rather than adjectives.** "Uses the spacing
step already used by its neighbors and introduces no new one" is a requirement.
"Feels polished" is not. Anything it cannot state checkably it flags as a
judgment call for 8b rather than smuggling in as prose.

### 4e. Admin capability

*Applies when: the change creates something that outlives the request — stored
records, accounts, uploads, scheduled work.*

Who can inspect, correct and remove what this creates; who is allowed to undo
it; and what happens to it when whoever owns it is gone. It asks the question
nobody else in the loop asks — **"and then who cleans this up?"** — which is the
question whose absence leaves data nobody can reach.

### 4f. Cybersecurity

*Applies when: the change accepts input its author did not write, or touches
credentials, permissions, or a network boundary.*

A threat model against the **real code**, not against the design. What a
legitimate but unauthorized party can reach, what an unauthenticated one can
reach, what an entry point accepts that it should not, secrets in logs and error
messages, and the injection surface.

Explicitly not a checklist review: it names an actor, a goal, and the concrete
path.

### 4g. Site reliability

*Applies when: the change runs somewhere other than the developer's machine.*

Failure modes, blast radius, rollback and observability. What breaks when a
dependency is **slow** rather than absent; what the operator sees when it does;
whether the change can be undone afterwards and by whom; and whether any alarm
it adds would survive contact with a legitimately persistent state rather than
firing until people stop reading it.

## Stage 8b: the same roles, against the real diff

Not a repeat. A design is a prediction and the diff is the outcome. Same role,
fresh reader, never the same context.

**A divergence from the design is not automatically a defect.** Ask whether the
implementation's choice was the better one. Where it was, adopt it and correct the
design record; where it was drift, fix it. A conformance pass that marks every
divergence as a violation is worse than no pass, because the fixer has no
authority to dismiss a finding and will implement the worse design.

## The four review agents (stage 10)

### 10a. Reviewer

Reads the **whole group's diff** with the acceptance criteria and the
architecture in hand.

This is not stage 8 repeated. Stage 8 audits one wave's files while the context
that dispatched them is still warm. This reads every change at once, with no
memory of why any of it seemed reasonable at the time. **Seams between agents
are only visible from here**: the duplicate helper two siblings each added, the
contract that drifted on one side, the error path handled in one layer and
swallowed in the next.

A change nobody can trace to an acceptance criterion is either scope creep or a
missing criterion, and both need saying.

Reports findings. Does not edit.

### 10b. Researcher

Runs **concurrently with the reviewer** — it needs the diff's dependency
surface, not the reviewer's opinion of it — and answers from current sources
rather than memory. Installed documentation and the vendor's own material are
authority over recollection. Treat a deprecation notice as a finding.

Performance comes back on the same footing as correctness, on the paths that
actually run: work repeated per item that could be hoisted, waits placed in
series with no dependency between them, a query per row where one query would
do, fields fetched that nobody reads, and a file read whole when it is consumed
in pieces.

Every quoted fact carries **its source and the date it was checked**. Facts that
outlive the review are promoted into the acceptance criteria.

Two limits, both learned:

- Do not relitigate a trade-off stage 4 already rejected. New evidence reopens
  it; a preference does not.
- An optimization with no measurement behind it and no reasoning about the real
  input size is a guess, and guesses are how a codebase acquires complexity it
  cannot later remove. **Say what the input size is, or leave the code alone.**

Reports findings. Does not edit.

### 10c. Aesthetics reviewer

*Applies when 4d applied.* Runs concurrently with the other two, over the whole
group's diff, holding the requirements it wrote at 4d.

Its distinct value at this scale is the **seam**, which no single-surface pass
can see: the same element presented two different ways in two places, three
constructions of one idea in one view, a state handled carefully in one place
and as a bare string in the next. Every one of those is invisible from inside
the file set that produced it.

Reports findings. Does not edit.

### 10d. Fixer

Receives every review report, merged and de-duplicated, and is the only one of
the review agents that touches the working tree. Same brief discipline as stage 6: an
explicit file list, and no git writes.

**It has no authority to dismiss a finding.** If a finding looks wrong, it says
so in its report and leaves the code as it was — a fixer that silently declines
turns a finding into a silence, and silence is indistinguishable from fixed.

Its changes are code like any other: they re-run the gates, and each one needs a
test that can fail.
