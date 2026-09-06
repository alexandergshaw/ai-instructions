# Development Loop

This document defines the working procedure for any AI coding agent making changes to this
repository. It is a control-plane file: it governs work performed **on** this repository and is
never distributed downstream. `scripts/validate.py` enforces that it stays out of `payload/`.

`AGENTS.md` states what must be true. This document states what to do, in what order, and what must
be proven before a change is considered complete.

## The governing principle

Scale the gate to **reach, not diff size**.

A mistake in an ordinary repository costs that repository. A mistake here is copied by automation
into repositories this project does not control, arrives there as a pull request that a human may
approve on the assumption that it was already checked, and in the worst case deletes downstream
content that nobody notices is gone.

The practical consequence is counter-intuitive and worth stating plainly. The three highest-risk
changes available in this repository are all small:

- a one-line change to the deletion path in `scripts/sync_payload.py`;
- a change to how `commit_changes` in `scripts/publish.py` builds its `git rm` set, which is what
  actually commits a deletion into a real repository;
- adding one entry to `config/targets.json`, or flipping one `enabled` flag, which points all of the
  above at a repository that has never received anything before.

A two-hundred-line rewrite of `README.md` is among the lowest.

## Step 0 — Classify before doing anything

State three things before making any edit:

1. **Layer** — control plane, `payload/`, or both. See `AGENTS.md` for the boundary.
2. **Tier** — T1, T2 or T3, from the table below.
3. **Version impact** — PATCH, MINOR or MAJOR, using the guidance in `AGENTS.md`.

`VERSION` is the version of the *distributed instructions*, not of this repository's tooling. A
control-plane change that leaves `payload/` untouched normally carries no version impact — say
"none" and move on. The exception is a change to synchronization semantics: what gets copied,
deleted, or recorded in the manifest. That is MAJOR even though no payload file changed, because
downstream repositories experience it as a behavior change.

One line is enough. If a change turns out to be a tier higher than first classified, say so and pick
up the additional gates before continuing rather than finishing under the original tier.

## Tiers

| Tier | Applies to | Required steps |
| --- | --- | --- |
| **T1 — Routine** | `README.md`, comments, typo and formatting fixes in an existing payload file that do not change what it requires, test-only additions | 0, 1, 2, 4, 5. No evaluator seats |
| **T2 — Standard** | New payload file or skill, any payload edit that changes what an instruction requires, new `scripts/validate.py` rule, `.github/workflows/validate.yml`, edits to `AGENTS.md` or to this document | 0–6; seats per the seat table |
| **T3 — Blast radius** | Any change to `scripts/sync_payload.py` or `scripts/publish.py`, manifest shape, `.github/workflows/sync-instructions.yml`, any change to the target list in `config/targets.json` including enabling an existing target, any release | All steps, the downstream-safety harness at step 5, and every seat its triggers call for |

A payload edit that changes what an instruction *requires* is T2 even when the diff is one word.
Changing "prefer" to "never" is a one-word change to the behavior of every downstream agent.

The T3 triggers name whole files rather than paths inside them. Enumerating sub-paths creates a gap
at exactly the wrong line: `load_previous_manifest` is neither the copy path nor the delete path,
yet it is the sole gate deciding what `remove_stale_files` is permitted to delete.

When a change spans tiers, the highest tier it touches governs the whole change.

## Steps

### 1. Acceptance criteria

Write observable, falsifiable criteria before writing code. For code changes in this repository a
criterion is almost always two-sided, because every capability has a matching safety obligation:

```text
Bad:  "stale files are cleaned up"

Good: "a file listed in the previous manifest and absent from the current payload is deleted,
       AND a file absent from both is left untouched,
       AND the downstream root CLAUDE.md is not modified"
```

A criterion that states only what should happen, without stating what must not, is incomplete.

For a payload change the criterion is about downstream behavior instead: state which agent behavior
the instruction is meant to change, and how someone would tell whether an agent complied with it.

### 2. Survey the existing implementation

Required at every tier. Read the code or prose that already exists and cite `file:line` before
proposing a change. Never pattern-match on a function name — read the body and its callers.
`AGENTS.md` requires inspecting the existing implementation before introducing new abstractions,
unconditionally, and this is where that happens.

### 3. Tests first (T2 and above, where there is a testable surface)

Tests land in `tests/` **failing**, derived from the acceptance criteria, before the implementation
is written. This repository is unusually well suited to it: the behavior under test is filesystem
manipulation inside a temporary directory, and the whole suite runs in under a second.

- Assert observable behavior — files present, files absent, file contents, exit codes, manifest
  contents. Never assert internal structure.
- An implementer may add **further** tests, but a test written at this step is never weakened,
  narrowed, or deleted to make an implementation pass. If a test appears to be wrong, that is a
  planning defect: report it rather than editing it away.
- Every new `scripts/validate.py` rule ships with a negative test. A validation rule with no test
  proving that it can fail is not a validation rule.

**Two exceptions, and only these two:**

- **Payload prose changes** have no testable surface beyond what `validate.py` already checks, and a
  file-exists assertion is exactly the vacuous test the Test seat is told to reject. Skip step 3 and
  open the Payload prose and Downstream advocate seats instead.
- **A change that escalated to T2 after implementation began** cannot honestly write its tests
  first. Write them immediately on escalation, and have the Test seat evaluate them before the Diff
  seat opens.

### 4. Implement

The smallest correct change that fully satisfies the criteria. No unrelated refactoring.

### 5. Verify

Run the gate and **paste the real output**. A summary of a command's result is not evidence that the
command was run.

```bash
python scripts/validate.py
```

```bash
python -m unittest discover -s tests -v
```

**A skipped test is not a passing test.** `OK (skipped=1)` is not a green run until you say which
test skipped and why. The symlink guards in the sync path skip entirely on Windows, so on that
platform the protections against a symlinked managed destination are unproven by the local suite.

Then read the complete `git diff`, not a summary of it.

**Any change under `scripts/` must additionally confirm** that synchronization is still idempotent
and that unmanaged downstream files are still protected. `AGENTS.md` requires both after *any*
Python or synchronization change, not only at T3.

**T3 additionally requires the downstream-safety harness.** These invariants live in
`tests/test_downstream_safety.py` and already execute under the command above — so a T3 change does
not re-run them as a separate ritual. It states, invariant by invariant, **which test proves it**,
and adds a test for any invariant the change introduces, weakens, or newly depends on.

Enforced by the code today, each with the test that proves it:

- Running a sync twice with identical inputs produces a byte-identical result.
- An unmanaged file under `.claude/`, and an unmanaged skill directory, survive a sync.
- A file dropped from the payload is deleted downstream only if the previous manifest listed it,
  and a sibling managed file is not disturbed by that deletion.
- A manifest whose `source` is foreign authorizes no deletions at all.
- A symlinked managed destination, or a symlinked parent, is refused rather than followed.
- **A manifest entry outside `.claude/` is refused, never deleted.** The downstream root
  `CLAUDE.md` and files under `src/` survive a manifest naming them
  (`test_manifest_entry_outside_managed_roots_is_skipped_not_deleted`,
  `test_manifest_naming_paths_outside_claude_deletes_nothing`), including when `.claude` appears
  deeper in the path (`test_managed_root_must_be_the_first_path_component`).
- **A refused entry is skipped, not fatal.** Delivery continues, and the rewritten manifest drops
  the entry, so a corrupted or planted manifest cannot freeze a repository into never receiving
  updates again (`test_refused_entry_does_not_block_delivery_or_later_syncs`).
- **Vetting happens before any deletion**, so a refusal partway through cannot leave a repository
  in a state neither manifest describes (`test_no_partial_deletion_when_a_later_entry_is_refused`).
- **Distribution is bounded by the same roots as cleanup**, in both the sync code and
  `scripts/validate.py`, so the two halves cannot drift apart
  (`test_payload_file_outside_managed_roots_is_rejected`,
  `test_payload_content_outside_managed_roots_is_rejected`).

Known gaps — real, and not to be described as covered:

- **Inside `.claude/`, the manifest is still fully trusted.** `MANAGED_ROOTS` bounds deletion to a
  top-level directory, which is broader than the ownership boundary `README.md` describes
  (`.claude/shared/**`, `.claude/skills/shared-*/**`, and the manifest). A manifest naming
  downstream-authored `.claude` content will still delete it. Narrowing the bound to that
  documented boundary is tracked work.
- **A downstream repository that gitignores `.claude/` is reported as a success while receiving
  nothing.** `repository_has_changes` sees a clean tree and `process_target` returns "no changes",
  so the target is counted among the successes forever.
- **The symlink refusals on the deletion path have no test on any platform**, and the one symlink
  test that exists covers the copy path and skips on Windows.

### 6. Peer evaluation (T2 and above)

Independent evaluators read the work adversarially before it is considered complete. Which seats are
required, how they are briefed, and how their findings are resolved are specified in
**Peer evaluation** below.

### 7. Release

Never automatic. Updating `VERSION`, creating a tag, publishing a release, or triggering the
distribution workflow happens only on an explicit request, and never as a side effect of finishing
a change.

## Peer evaluation

### The rule

**At T2 and above, an artifact is never evaluated by whoever produced it.** This holds for every
artifact the tier's seats cover, and it binds the agent orchestrating the work as much as any agent
it delegates to. Catching yourself about to grade your own classification, your own acceptance
criteria, or your own diff is the signal to hand it to an evaluator instead.

T1 opens no seats and is reviewed by its author alone. That is a deliberate trade: a README typo
does not earn a review panel, and pretending otherwise is how a process gets ignored wholesale. It
is also the reason the T1 trigger list is written narrowly.

The value of an evaluator is that it was not present for the reasoning. An author cannot help
supplying from memory what its own artifact fails to state; a fresh reader cannot, which is exactly
why it finds the gap. That property is destroyed the moment an author reviews itself, and it is
weakened whenever an evaluator is shown a previous evaluator's conclusions before forming its own.

**A seat is a separate agent**, with its own context, that did not author the artifact. A section in
the author's own reply headed "Diff seat: no findings" is not a seat and does not satisfy this step.

**Spawning evaluators is authorized by this document.** No agent needs to stop and ask permission to
open an evaluator seat that its tier requires.

### Seats

| Seat | Evaluates | Required at |
| --- | --- | --- |
| **Classification** | The step 0 tier and version-impact call | T2 and above |
| **Criteria** | The acceptance criteria from step 1 | T2 and above |
| **Test** | The failing tests from step 3, before implementation begins | T2 and above, where step 3 applies |
| **Diff** | The whole implementation as one change | T2 and above |
| **External contract** | Every fact the change depends on that lives outside this repository | Any change touching `gh`, `git` invocation, GitHub Actions, or the GitHub App |
| **Downstream advocate** | The change as a downstream maintainer would receive it | T3, and any `payload/` change at T2 or above |
| **Payload prose** | Distributed instruction text as an instruction, not as writing | Any `payload/` change at T2 or above |
| **Remediation** | Applies adjudicated findings; evaluates nothing | T3 |

The seat table is the authority on which seats open; the tier table is the authority on which tier
applies. A seat whose trigger does not fire is not opened — a mandatory seat with no applicable
question is worse than no seat, because it trains everyone that "no findings" is the normal return.

### The classification seat is the highest-leverage one

It is listed first because it governs every other gate. A change to `scripts/sync_payload.py`
misfiled as T1 silently cancels the downstream-safety harness, the diff evaluator, and every other
seat at once — and nothing downstream of the misclassification will notice, because each later step
is behaving correctly for the tier it was told it was in. Evaluating the tier call costs one short
pass and protects everything after it.

Its question is narrow: given the files this change actually touches, is the stated tier right, and
is the version impact right? It reads the real file list, not the author's description of it.

### What each seat is asked

- **Classification** — Does the diff touch anything in a higher tier's trigger list? Is a change to
  synchronization semantics being shipped as PATCH? Does it change the manifest's shape, `source`,
  or `schemaVersion` without saying so?
- **Criteria** — Is any criterion unobservable, unfalsifiable, or actually two criteria? Which
  criterion states only what should happen and omits what must not? What does the request require
  that no criterion covers?
- **Test** — Does each test actually fail when the behavior it names is broken? Prove it by breaking
  the code in a scratch copy, not by reading the test. Are any assertions vacuous — passing whether
  or not the code exists? Does the set cover the criteria? Does any test assert internal structure
  instead of observable behavior?
- **Diff** — What is wrong with the code? It reads the change as a whole, which is the thing no
  individual author can do: a defect living in the seam between two files — a contract honored
  differently on each side, one half of a pair updated, a comment describing machinery that was
  removed — is invisible to each author by construction and is precisely what this seat exists to
  catch.
- **External contract** — Are the `gh` subcommands and flags real and current? Do the pinned actions
  take the input names the workflow passes them? Is the Actions expression syntax valid? For a new
  target: does the repository exist, is the App installed on it, and what is its default branch?
  Each answer comes from the vendor's own documentation, never from recollection and never from
  another agent's summary. These are the errors the local suite structurally cannot catch, and they
  surface for the first time during a real distribution run against real repositories.
- **Downstream advocate** — Read this as the maintainer of a repository that did not ask for it. Is
  the pull request reviewable, or is it a wall of churn? Does it touch anything the downstream
  repository owns? If it deleted something it should not have, would the diff make that visible or
  bury it? Is the commit message accurate about what changed? Does anything user-facing assume a
  particular vendor's agent, when `AGENTS.md` requires vendor neutrality?
- **Payload prose** — Judge distributed text as an instruction an agent will act on, not as prose a
  human will read. Which rule is an adjective an agent satisfies by assertion? Which would an agent
  be caught violating? Does any rule contradict another distributed rule, or assume knowledge of
  this central repository that a downstream agent does not have?

### Briefing an evaluator

Every evaluator brief states:

- **The adversarial task.** Its job is to find defects, not to confirm the work is done. Where it is
  uncertain, the default is "defective." An evaluator that returns "looks good" without having tried
  to break the artifact has not done the job, and a seat reporting zero findings says what it tried.
- **Independent authorship of the artifact.** Word it generically: the artifact under evaluation was
  produced by someone else, who is not available to explain it, and it should be graded as a
  competitor would grade it. Scope this framing to **the artifact, never the repository** — the
  evaluator must judge against `AGENTS.md` and `.claude/rules/**`, and cannot both distrust the
  repository and use its policy as the standard. The framing is for the brief only: it never appears
  in commits, code comments, or anything user-facing.
- **The domain.** This repository's domain is multi-repository automation, GitHub Actions security,
  and the design of instructions that other AI agents execute. A generically correct answer here is
  routinely domain-wrong: code that is fine against one repository is wrong against fifty; a
  destructive operation that is ordinary in a local script is unacceptable against a repository the
  operator does not own; prose that reads well to a human can be unfalsifiable to an agent.
- **Evidence requirements.** Findings cite `file:line` or quote real command output. An assertion
  without evidence is not a finding.
- **Scope limits.** The files it may read and touch, no `git` writes, and the instruction to stop
  and report rather than expand scope.

### Independence

Evaluators that can run at once are spawned in a single batch so they run concurrently, and they are
**blind to each other's findings**. Two independent passes over the same artifact beat one pass
anchored on the other's conclusions. The Diff seat and the External contract seat are disjoint by
construction — one reads this repository, the other reads the outside world — and neither is shown
the other's report.

Fan evaluators out **by defect, not by file**. A flaw that exists in two places gets missed when
each evaluator is told the other half belongs to someone else.

### Adjudication

Evaluator output is a proposal, not a verdict — including on questions of fact. Before anything is
edited:

1. **Verify the load-bearing claims yourself.** An evaluator's factual claim about what the code
   does is checked by running the code, not by reading the report. This runs in both directions: a
   claim that the author's document is wrong is verified before the document is changed.
2. Merge the reports and resolve contradictions on evidence, by reading the artifacts rather than by
   refereeing between two assertions. Evaluators disagreeing is useful signal, not noise.
3. Drop findings that do not survive that verification, and only those. "Did not survive scrutiny"
   means a specific check contradicted the finding — not that it looked unlikely or would be
   inconvenient to act on. A "cleaner" or "faster" change that costs clarity or correctness is
   rejected, and the rejection is recorded like any other.
4. Hand whoever applies the fixes **one coherent instruction set** — never two evaluators' raw
   reports to reconcile on their own.
5. Record every finding not acted on, with its reason, in the same place as the accepted ones, so
   the record shows what was seen and declined rather than only what was fixed.

At T3 the agent applying the fixes is neither of the evaluators that found them. An agent that found
a problem is the worst judge of whether its own fix is right.

**A decision to accept a deviation is itself evaluated.** Waving through "close enough" is the
easiest place in this loop for drift to enter, so the acceptance gets attacked directly, not just
the code.

### Two failure modes worth naming

**Consistency is not correctness.** "This is how the repository already does it" is evidence about
consistency and nothing more. A pattern copied ten times is wrong ten times, and a convention that
predates a tooling change can be actively harmful now.

**Self-reports are unreliable in both directions.** Check what an agent claims against
`git status --short` and the actual diff before trusting the report or opening the next seat.

### Termination

Re-evaluate after fixes until a pass produces no **material** finding — meaning one that would
change a file, a criterion, or the tier. Wording preferences and restatements of findings already
recorded are not material.

**Stop after three passes.** A seat still producing material findings on a fourth is evidence that
the problem is upstream — usually the acceptance criteria or the tier call — and the fix is to
return to that step, not to keep patching the diff.

Every code change re-enters evaluation, including one-line fixes made under time pressure at the end
of a change. That code is the least reviewed in the whole change and the most likely to introduce a
second defect while closing the first; the size of a fix predicts nothing about the size of what it
breaks.

## Standing rules

**Never touch a real downstream repository.** Development and testing use temporary local
directories. Integration testing against GitHub uses a dedicated throwaway repository, never a
production, classroom, or active development repository.

**The manifest is a wire format, and it is untrusted input.**
`.claude/.central-instructions-manifest.json` is a contract with every repository already synced, and
it is also a file that lives in a repository this project does not own — it can be corrupted,
hand-edited, or planted, and `remove_stale_files` acts on whatever it names.

Changing its `source` value or the shape of its paths is a MAJOR change and requires a stated
compatibility story. The failure mode is narrower than it first appears, and worth stating exactly,
because a migration built on the wrong model will address the wrong risk: after a `source` change,
`load_previous_manifest` treats the old manifest as managing nothing, but `copy_payload` still
copies every payload file unconditionally and `write_manifest` immediately re-adopts under the new
source. So **content keeps updating and management re-establishes itself on the very first sync.**
What is permanently lost is narrower: any file dropped from the payload during that same changeover
is never deleted downstream and is absent from the new manifest too, making it permanently invisible
to the system. A `source` change therefore needs a one-time deletion reconciliation, not a
re-adoption plan.

`schemaVersion` is written but never read — `load_previous_manifest` does not inspect it. Treat that
as a gap rather than as protection: an incompatible future manifest shape will be silently
mis-parsed rather than rejected.

**Never weaken a safety invariant to make a test pass.** If a test fails against an invariant, the
change is wrong until proven otherwise. Deleting the test, loosening the assertion, and narrowing
the validation rule are all the same error.

**Verify external details against primary sources.** The `gh` subcommands and flags, the input names
of pinned GitHub Actions, and GitHub Actions expression syntax are facts that live outside this
repository. The local test suite cannot catch an error in any of them, and a mistake surfaces for
the first time during a real distribution run against real repositories. Confirm each against the
vendor's own documentation rather than recollection.

**Evidence over assertion.** Cite `file:line`. Quote real command output. "The tests pass" is a
claim; the pasted output of the test run is evidence. This applies equally to work reported by a
subagent — check a returning agent's claims against `git status --short` and the diff rather than
trusting the report.

**Payload prose must be checkable, not adjectives.** Files under `payload/` are instructions that
other agents will act on, which makes them this repository's real user surface. "Write clean code"
is an adjective an agent satisfies by assertion. "Do not delete tests to make a suite pass" is a
rule an agent can be caught violating. Every distributed instruction should be falsifiable in the
same way an acceptance criterion is.

**One failure never stops the rest.** This holds in the code, where one downstream target failing
must not prevent attempts against the remaining targets, and in the work, where one blocked item
does not justify leaving the others undone.

## Relationship to the other instruction files

```text
AGENTS.md                  policy — what must be true, and who owns what
DEVELOPMENT-LOOP.md        procedure — what to do, in what order, and what to prove
.claude/rules/**           scoped rules for particular areas of this repository
payload/**                 instructions distributed to downstream repositories
```

Where this document and `AGENTS.md` appear to conflict, `AGENTS.md` governs, and the conflict is a
defect in this document worth fixing.
