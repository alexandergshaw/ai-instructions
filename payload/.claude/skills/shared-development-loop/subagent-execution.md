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
  criteria, the reuse survey, the plan, the implementation, and the stage 8
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

- **Every stage 4 pass and every stage 10 agent takes the highest model
  available.** These are the roles whose output everything downstream inherits;
  a miss here is re-litigated by every agent after it.
- **Implementation takes the faster, cheaper tier. Verification takes the
  stronger tier.** The implementer and the verifier are never the same agent and
  never the same model class.
- **Pin an explicit version, never a bare family alias.** An alias resolves to
  whatever is newest, which silently changes both cost and behavior between two
  runs of the same loop.

Where a surface accepts only a family name rather than a version string, say so
in the report rather than assuming the pin took effect.

**This loop is expensive by design.** A change that triggers every role costs
seven pre-code agents, seven follow-ups at stage 8b, and four at stage 10,
before any implementer. Someone pays for that. Run the roles whose triggers
actually fire — see `roles.md` — rather than all eleven by reflex, and say what the run will cost
before starting it.

## Dispatch mechanics

**Spawn concurrent agents in a single message** so they genuinely run in
parallel. Seven pre-code passes dispatched one at a time are seven round trips,
and each one's framing contaminates the next.

**Concurrent agents must hold disjoint file sets**, proven against the real file
list before dispatch. Every brief names the files the agent owns *and* the files
its siblings own, with an instruction to stop and report rather than touch one
of theirs.

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
   destroys the check in stage 7.
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

## Verifying what came back

Self-reports are unreliable in both directions. Before trusting a report or
dispatching the next wave, compare the working tree against the assignment, and
spot-check the specific claims: if an agent says it reused an existing helper,
grep for it.
