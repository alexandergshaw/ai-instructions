# Seat triage, and the backstop that makes it safe to be wrong

Which design seats run is decided from the *planned* change, before the code exists. Record the
trigger that fired for each seat that runs, and the reason for each that does not, alongside the
acceptance criteria.

**A seat runs unless the triage artifact quotes the `file:line` in the plan that makes its trigger
impossible.** An uncited "not applicable" runs the seat. Uncertainty is unobservable and
self-reported, so it cannot be the thing that decides.

The triage artifact is checked like any other, and its checker attacks one question hardest: **which
trigger fires that the triage skipped?**

## Trigger table

Adapt the nouns to what this repository actually builds.

| Seat | Runs when |
|---|---|
| Criteria, design, reuse survey, plan, tests, verify, unit tests, whole-diff review | **always** |
| **UX** | anything a person operates changes — a rendered surface, a command-line interface, copy, a state, a path through a task |
| **Aesthetics** | a visual element changes: layout, styling, tokens, icons, empty/loading/error states. Copy-only changes fire UX without aesthetics |
| **Data** | a read or write is added or changed — database, network, storage, cache, or a dependency that causes a re-fetch — or the shape of a record or key changes |
| **Operability** | new persisted state, a new delete, a new privileged call site, a new log or downloadable artifact, or a failure only the affected person could ever see |
| **Security** | a route or authorization, a query filter, secrets or environment, untrusted input reaching a model, a network call, the rendered page, a log or a download; any change to what a prompt sends; any new egress of someone's content |
| **Reliability** | multi-step writes, a new external call, a retry, timeout or limit, a changed error handler — *can it now present a degraded state as a confident negative?* — concurrency such as a double click or two tabs, or a latency requirement |
| **Accessibility** | a rendered surface, a generated document, focus management, timing or auto-dismiss, live-region cadence |
| **External facts** | the plan rests on any fact outside this repository — **re-triaged by the plan's checker** |
| **Baseline** | the area has no existing regression coverage |
| **Researcher** | the diff touches a hot path — per render, per keystroke, per item, or a network fan-out — or leans on framework or platform behaviour nobody has checked against current sources |

## The backstop

Triage is a judgement made before the code exists, so it will sometimes be wrong. The fix is not
better judgement; it is a mechanical backstop.

Define **one raw pattern per triaged-out seat**, run over the changed non-test, non-comment lines of
the diff and over its file paths. **A hit does not run the seat** — it guarantees the verify step
*looked*. The verify step rules on **every** triaged-out seat, hit or not, with evidence, and its
ruling must cite every hit.

Three rules make this an instrument rather than theatre.

**"The diff" means tracked modifications plus every file the chunk created.** Agents often cannot
stage files, so a plain diff never shows a new file. Assemble it explicitly — the tracked diff plus
the list of new untracked files — and never run the patterns over the whole tree, where build output
drowns the signal.

**Each pattern is canaried before a clean result is trusted:** it must match a string you know is a
hit, and miss one you know is not. **A pattern whose canary cannot be constructed forces its seat to
run.** In a repository with no network and no interface there may be no known hit for the security
or accessibility pattern anywhere in the tree; that is not permission to skip the check, it is the
signal that the instrument cannot speak and the seat decides instead.

**Words that fire on nearly every change here must be excluded deliberately**, or the instrument is
all noise. If exclusion would empty the pattern, the pattern cannot discriminate — force the seat.

A forced seat — one the verify step rules as holding — is a **triage miss**. Say so in the report,
and widen that trigger for next time.
