# The decisions ledger, and artifact hygiene

## The ledger

The only design document every consumer reads in full. A consumer opens a full seat artifact only
for its own seat.

```text
| ID | seat | requirement (checkable) | evidence (symbol / test title / file:line) | status |
```

`status` is one of: **ruled** · **accepted-risk (who accepted it)** · **rejected: reason**.

Seats propose their rows at the end of their own artifact. **Rows reach the ledger as the seat wrote
them — copied exactly, never retyped or summarized.** The orchestrator adds only the status column.

Where this repository keeps working documents, the ledger lives there. Where it keeps none, it lives
in the orchestrator's report for the chunk — not in a new file, and not in a commit message.

A requirement that is not checkable does not belong in the ledger. "Feels responsive" is not a
requirement; "the list renders without a second round trip, asserted by <test title>" is.

## A gap ruling cites its source

Before filling a gap a seat reports — "the design leaves X unspecified" — search the design for X
and either **quote the text that decides it** or **quote the absence you found**. Ruling on a gap
that was already specified elsewhere is how contradictions get authored.

## Artifacts

**An artifact is written by its seat, or saved exactly as the seat returned it — never retyped by
the orchestrator.** Retyping hands every checker a lossy transcription instead of the original, and
a checker cannot tell a transcription error from the author's mistake.

**One file per artifact per round**, named so the round is part of the name — `<seat>.r2.md` rather
than `<seat>.md`. An existence check must not be able to pass on the previous round's file.

**Scratch directories are not durable storage.** Anything that must outlive the session belongs
somewhere the repository actually keeps things. Where it has nowhere, say so in the report rather
than creating a location.

## Record at disposal, not at the end

A queue item that lives only in a scratch file or inside a subagent's report is a deletion with
extra steps — nothing reads those at the start of the next piece of work.

When a check disposes of a finding as "later", write it to the durable place **then**, at the moment
of disposal. Reconcile the list when the chunk completes.
