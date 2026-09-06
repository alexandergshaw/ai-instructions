# Development Loop

The principles that hold for any change, whether or not the full procedure is
running. The twelve-stage procedure, the peer roles, and the rules for
dispatching concurrent agents live in the `shared-development-loop` skill.

## The core principle

**Author is never checker, for every artifact — not just code.**

An agent that produced a thing is the worst available judge of whether it is
right. That applies to an acceptance-criteria document, an architecture, a
survey, a test and a fix exactly as it applies to a feature. Every artifact is
adversarially checked by a fresh reader before its consumer relies on it, and
the chain ends only on a clean check.

Two consequences that are easy to skip and expensive to skip:

- **Whoever coordinates the work does not also perform its architecture or its
  review.** Doing either in the same context that wrote the acceptance criteria
  destroys the only property that makes those steps worth running: a reader who
  has nothing but the documents, which is exactly what an implementer has.
- **A check is itself an artifact, and it can fail silently.** A sabotage that
  never actually applied reports green, and looks identical to a test that
  cannot fail.

## Never combine two roles in one agent

Whatever the roles are — author and checker, two different review perspectives,
implementer and verifier — they go to separate agents, however adjacent they
look. Separate readers genuinely disagree with each other, and a disagreement
between two of them is itself a finding. One agent wearing several hats writes a
single reconciled narrative and silently drops whichever concern it found least
interesting, which is exactly the concern nobody else was going to raise.

## Brief every checking role as a domain expert, and name the domain

A generic reviewer checks that a value is computed correctly. A domain reviewer
asks whether the result is defensible to the person it is shown to. State in
every peer-level brief what the reader is an expert in, drawn from what this
repository actually does.

This file does not decide the domain — the repository's own instructions do.
Where a repository has not named one, say so in the brief rather than silently
defaulting to a generic software agent.

## Non-negotiables

**Acceptance criteria before code**, numbered so they can be cited. Acceptance
criteria fix what would otherwise be invented differently by each person who
touches the work: exact signatures and return shapes, exact parameter names sent
to any external service, exact error messages where the wording is load-bearing,
and which file owns what. Verified external facts go in with their source and
the date they were checked.

**Verify reuse by reading the candidate and its call sites** — never by its
name, its neighbors, or a memory of it. A helper's signature does not tell you
that its second parameter is always unset in practice, or that its one existing
caller passes a shape your change cannot produce.

**Tests must be able to fail.** See `.claude/shared/testing/general.md` for how
to prove it and for the catalogue of tests that cannot.

**Reachability is a first-class check.** A capability can pass every gate and
ship dead. Trace each one from the entry point a user actually reaches to the
code that performs it. A value that is computed and never surfaced, and an error
whose reason never reaches whoever needs it, both pass every automated gate.

**Preserve the reason a failure happened.** Collapsing distinct failures into
one indistinguishable state is among the most common defects this loop catches.

**Say what you had to guess.** Every guess is a line the acceptance criteria
failed to write, and the guesses are where the next defect lives.

## The floor

The rules bounding what may be done without being asked — never commit, push,
open a pull request or merge unprompted, and never start the next piece of work
on your own — are in the `shared-agent-floor` skill, which is distributed to
every repository this system reaches.

They are stated once, there, so the two copies cannot drift. Nothing in this
loop lifts them.
