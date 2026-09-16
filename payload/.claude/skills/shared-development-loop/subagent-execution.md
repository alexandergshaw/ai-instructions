# Dispatching Concurrent Agents

The loop and its role briefs describe *what* must be checked and *by whom
relative to the author*, not which product runs them. This file carries the
parts that apply only when the agent running the loop can dispatch other agents
and choose a model for each.

## If your agent cannot dispatch other agents

The core principle does not bend: **whoever wrote an artifact does not check
it.** An agent that cannot dispatch cannot satisfy that on its own, so do not
claim the loop ran. Instead:

- Run the stages that are genuinely single-context work — the acceptance
  criteria, the reuse survey, the plan, the implementation, and the step 8
  audit of what landed.
- **State plainly which checks were not independently performed**, and treat
  their findings as unverified. A pass an author ran over its own work is
  evidence about care, not about correctness.
- Where any role's trigger fired and could not be independently run, ask for a
  human reviewer, or for the work to be re-read in a fresh session that has only
  the documents.

Running every role sequentially in one context and calling it done is the
failure the core principle exists to prevent.

## Model selection

Tiers, and the rule about defining agent types rather than overriding a model per call, are in
`roles.md`.

## What actually costs

Two facts that should shape dispatch rather than be rediscovered.

**Output tokens cost several times what input tokens cost.** So **point agents at paths; never paste
reference text into a brief.** Pasted context is billed as your output to deliver text the agent
could have read itself. The same applies to artifacts: have the seat write the file, or save what it
returned byte for byte — never retype it.

**Round count is the only lever with an order of magnitude behind it.** One avoided remediation
round saves more than any effort or tier adjustment across the whole chunk. Note the tension
honestly: sharper checkers *cause* more remediation rounds. That is the trade you want, but
"sharpen the checkers" and "spend less" pull against each other harder than they look.

**This loop is expensive by design.** A change that triggers every role costs
the design seats at step 2, their follow-ups at step 9, and the review agents at step 12,
before any implementer. Someone pays for that. Run the roles whose triggers
actually fire — see `roles.md` — rather than all eleven by reflex, and say what the run will cost
before starting it.

## Dispatch mechanics

**Spawn concurrent agents in a single message** so they genuinely run in
parallel. Seven pre-code passes dispatched one at a time are seven round trips,
and each one's framing contaminates the next.

**Disjointness has two halves, and both must hold.**

1. **Exact-path disjointness, computed, never eyeballed.** An item's file set is the files it edits
   **plus the tests that assert on the behaviour it changes**. Intersect the sets mechanically and
   show the result; an empty intersection is the evidence, not your reading of the lists.
2. **Informational independence.** For each pair, list the facts one item's artifacts state that the
   other's plan cites. A non-empty list means they are coupled however disjoint their files are —
   sequence them, or extract the shared contract into its own earlier step, alone. **State the list
   even when it is empty.**

Then a **third check**: every caller and assertion that currently passes *because of* the behaviour
about to change, each classified **owned** (this item changes it), **adopted** (this item takes
responsibility for it), or **checked-safe** — the assertion is quoted with its current passing
output now, and the item's brief names it as one that must be re-run and re-quoted before that item
reports done. An unquoted "checked-safe" is not one, and one never re-quoted after the change is an
unverified item rather than a safe one.

**Cap a concurrent wave at two or three items that write.** Larger fan-outs produce duplicated
discovery — several agents independently finding the same blocker, and one designing a fix for a
problem a sibling is concurrently proving does not exist. Read-only seats, which hold an empty
allowed-files list, are independent by construction and dispatch together.

Every brief names the files the agent owns *and* the files its siblings own, with an instruction to
stop and report rather than touch one of theirs.

**Blind concurrent reviewers to each other's findings.** Two independent passes
over the same diff beat one pass anchored on the other's conclusions. The
reviewer reads the repository; the researcher reads the outside world; neither
sees the other's report before writing its own.

**Fan agents out by defect, not by file.** A flaw that exists in two places is
missed when each agent is told the other half belongs to someone else.

## Brief template

Every dispatched brief states:

1. **The acceptance criteria, to be read in full first**, and an instruction to
   code against them rather than against files that may not exist on disk yet. A
   sibling's missing module is reported, never created or inlined.
2. **The role**, and that it is the only role this agent holds.
3. **The domain** this repository works in, and that the agent is an expert in
   it.
4. **For a checking role**, that its job is to find defects rather than confirm
   the work, that uncertainty defaults to "defective", and that it should judge
   the work as an outside reviewer who was not present for the reasoning. This
   framing stays in the brief and never reaches anything user-facing.
5. **The exact file allow-list**, plus the files its siblings hold, and an
   instruction to stop and report rather than reach outside it.
6. **No git writes.** Not `stash`, `commit`, `checkout`, `restore`, or `reset`.
   One agent's stash reverts every sibling's work, and a commit mid-wave
   destroys the check at step 8.
7. **"0 errors AND 0 warnings"**, stated in those terms. An agent told only "no
   errors" reports success over a wall of warnings, including ones it
   introduced.
8. **The evidence standard** — findings cite file and line, or quote real
   command output. An assertion without evidence is not a finding.
9. **What to return** — the file list it actually touched, and what it had to
   guess.

A checking role that returns no findings states what it tried to break. A
checking role whose subject this repository does not have says so in one line
rather than inventing findings.

## Telling a seat something mid-run

When a ruling moves while a seat is still building on it, **tell that seat while it is running** — a
message reaches it at its next step and costs far less than a rework round. Never revise criteria
while a plan is being written against them; hold the revision until the plan lands and fold both
into one round, or tell the plan's author exactly what is moving.

**Resuming a finished agent is not cheap** — it costs about what a fresh run costs. Batch small
rulings into the next round instead of reopening a completed one.

## Escalation

The same item failing verification twice from the mid tier gets re-dispatched at the next tier up
for the remaining rounds. Verification stays at the strongest tier regardless.

## Verifying what came back

Self-reports are unreliable in both directions. Before trusting a report or
dispatching the next wave, compare the working tree against the assignment, and
spot-check the specific claims: if an agent says it reused an existing helper,
grep for it.
