# Checks

Every artifact any agent writes is checked **before its consumer reads it**, by a fresh agent that
is neither its author nor the orchestrator.

## A check without a control is not a check

An instrument counts as a check only if something fires when **the instrument itself** is broken: a
no-op mutant that must survive, a canary pattern that must hit alongside one that must not, a
summary line that must be present. A search returning nothing because it was malformed looks exactly
like a search returning nothing because the thing is absent.

**A control is blind to the agent it tests.** It is planted by someone other than that agent,
indistinguishable from the real items, and never chosen by the agent it tests.

**A gate on a path that does not change needs a freshness control.** It must fail against the
previous round's file, or it is proving nothing.

## Grouping along the seams

Seats whose artifacts must agree get **one** checker that reads all of them plus the reconciliation
ruling, and is told to attack the seams — where they contradict, and what each assumes another
covers. Natural groups: design and data; experience and craft; operability, security and
reliability.

"Attack the seams" is not an instruction an agent can satisfy by saying it did. Concretely: **list
every contract named in two or more artifacts, quote both statements verbatim, and rule identical or
divergent.** A seam list of length zero must name which artifacts were compared.

A ruling that resolves a conflict between different groups goes to every group checker it touches.

## When two agents disagree

On a **fact**, demand the measurement — what was measured, how many rows could have failed, and
permission for a third answer neither proposed. The orchestrator rules only on **value trade-offs**,
never on facts.

A rejected finding is resolved on evidence and recorded with its reason, in the same place as the
accepted ones.

## Termination

A clean check ends the chain. Findings go back to the author, and the re-check is a **delta
re-check** whose brief carries three things: what changed, the artifact's **new inventions — attack
these hardest**, and a "confirmed sound, do not re-litigate" list.

**At the third round on one artifact, stop patching instances and close the class.** Closing the
class means: name the property that makes every instance defective, say where that property is now
enforced once, and list every instance the search for it returned — **including instances outside
this diff**. Then raise it to the person rather than starting a fourth round, and say which step you
believe is upstream of the repeated findings.

## When no check is warranted

If the changed-file list yields nothing outside documentation or comments, skip the adversarial
check and **record the skip**. Make this mechanical, not a judgement call — a checker briefed to
attack a comment fix has no mutant to build, and asking for one teaches that empty findings are
normal.

## The sampling rule

Where a bucket of results is reported by an agent rather than by an instrument, a fresh checker
re-executes at least **max(3, 20%)** of the reported passes, **choosing them from case identifiers,
never from the runner's own evidence strings**, and quoting real output for each.

Among those identifiers sits a **blind control** — a copy of a real case with a deliberately wrong
expectation, planted under a fresh identifier by someone other than the checker — **which must come
back failing**. Any sampled pass that fails, or a control that comes back passing, **voids the
bucket**, which is re-run.

Where the only cases available are files holding submitted or assessed work, do not plant a control
in them. Say the bucket could not be controlled, and report it as unverified rather than as passed.

## Re-entry

One rule for every way back into an earlier step — a forced seat, a late external fact, an RCA or a
review finding that changes a requirement.

**The change enters where it would have entered before any code existed**: the seat's artifact →
reconciliation into the ledger → that group's check. Then **everything downstream that consumed what
changed re-runs.** If the file set widens, redo the disjointness proof.

**Naming a shorter chain is a defect.**
