# Traps

Failure modes that have actually happened. They are the reason for the rules elsewhere in this
skill. The test-specific catalogue lives in `.claude/shared/testing/general.md` and is not repeated
here.

## Measurement and criteria

**Zero-power measurements.** A criterion satisfied by a comment containing the right words measures
nothing. Every criterion states how it resists that — what an agent would have to actually do, and
what output proves it.

**A failed instrument is invalid, not zero.** If the apparatus broke you have no reading, not a
reading of zero. Distinguish "nothing was wrong" from "this did not run" in the output itself, so a
later reader cannot mistake one for the other.

**A held-out set must be derivable, not stored beside the thing it tests.** A lookup table of known
answers passes every visible case and ships the held-out one broken. "Held out by instruction" is
not held out.

**A refusal nobody can act on is a dead end**, and a citation that does not resolve to something
checkable is not a citation.

## Search and absence

**Never write "nothing does X" from one search.** The false-absence mechanisms: result caps; code
that exists but is unreachable; an exclusion filter left on; a root that was too narrow; and
renames.

**Every absence claim needs a canary** — a pattern that must hit, run on the same instrument. See
the instrument rule in `checks.md`.

**Comments go stale and lie.** Cite the code, not the comment above it.

## Orchestration

**Fan out only across non-overlapping file sets.** A shared contract goes in its own earlier wave,
alone.

**An agent that mutates source needs a private copy, not a turn.** Two agents mutating one file
concurrently is unrecoverable, and taking turns does not make it safe — it makes the collision
intermittent.

**Check the tree after every returning wave**, before trusting a report or dispatching the next one.
Self-reports are unreliable in both directions. Spot-check the specific claims: if an agent says it
reused an existing helper, search for it.

**The tell that work has been reverted is a file you expect to be modified showing clean.** Recover
by path, never by restoring a whole stashed state over a tree other agents have since written to.
This is why no dispatched brief permits git writes.

**Diff hygiene after agent edits:** quote characters replaced with lookalikes, stray backup files
left beside the original, an import written at the wrong depth — which often only a build catches —
and a stale log read as if it were from the current run.

**Run the full suite once per chunk, at the end, on a settled tree, and run it yourself.** Say so in
every brief: a seat left to its own devices starts one and then stalls waiting on it. Per-round
agents get a scoped check instead. This is a latency rule, not a cost one — a suite run is cheap in
tokens and expensive in wall clock.
