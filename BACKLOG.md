# Backlog

Outstanding work on this repository. This file is the durable queue — the payload tells downstream
repositories that *"a queue item that lives only in a scratch file or inside a subagent's report is
a deletion with extra steps"*, and this is where that rule applies here.

## How to use it

**Record at disposal, not at the end.** When a review disposes of a finding as "later", it is
appended then, not when the session wraps up.

**A defect in the change currently under review may not be filed here.** Only pre-existing or
genuinely out-of-scope work qualifies. Deferring a live finding to the backlog is not a disposal, it
is a bypass — and it is strictly easier than either fixing or declining it, which is what makes it
dangerous.

**`Tier` is advisory.** It records what the tier looked like when the entry was written, against a
codebase that has since moved. Re-derive it at step 0 before starting; `DEVELOPMENT-LOOP.md`'s
classification seat still applies. Note that a one-line edit to `scripts/sync_payload.py`,
`scripts/publish.py`, `config/targets.json` or `.github/workflows/sync-instructions.yml` is T3
regardless of how small it looks.

**`Kind` decides what "done" means.**

- `fix` — closes with a diff.
- `decision` — closes by recording the decision and its rationale **in the entry**, never by
  implementing it. An agent that believes it knows the answer proposes it and stops.
- `investigation` — closes by recording what was found, which may be "no action needed".

**A `hazard` entry is never picked up as fill-in work.** It requires an explicit request naming the
entry ID. These touch the paths that delete or overwrite files in repositories this project does not
own, or that hold credentials.

**Evidence must survive the code moving.** A bare `file:line` rots silently, and a rotted line
number is worse than none because it looks authoritative. Prefer a command that re-locates the site
by content, plus a quoted anchor. Stamp it `as of <sha>`.

**Closing.** An entry closes only with evidence — a commit, a test name, or command output.
Declined entries are not deleted; they keep their reason, so the same finding is not rediscovered
every review. Move closed and declined entries to `## Closed` at the bottom.

**Status:** `open` · `in progress` · `done` · `declined` · `stale` (evidence no longer resolves;
needs re-verification before work).

---

## Downstream safety

### BL-01 — `copy_payload` overwrites unmanaged downstream files · `fix` · T3 · **hazard**

The copy-side twin of the deletion hole closed in `744d8d2`. `shutil.copy2` runs unconditionally
with no check that the destination pre-existed unmanaged.

- **Evidence:** `grep -n "shutil.copy2" scripts/sync_payload.py` → `shutil.copy2(source, destination)`, as of `b14d7fa`. Reproduced in review: a downstream-authored file inside a skill directory was replaced with no warning.
- **Why it matters:** the payload now ships generically-named files (`roles.md`, `checks.md`) inside skill directories, which makes the collision realistic rather than theoretical.
- **Done when:** an unmanaged downstream file at a payload destination is not silently replaced, **and** a file already recorded in the previous manifest still updates, **and** a first sync after a `source` change still re-adopts every payload file, **and** `tests/test_downstream_safety.py` passes unchanged.
- **Depends on:** coupled with BL-02 — these are the copy and delete halves of one ownership boundary. Fixing either alone leaves the halves inconsistent.
- **Found by:** Diff seat, profiles review. **First seen:** 2026-09-15.
- **Status:** open

### BL-02 — `MANAGED_ROOTS` is broader than the documented ownership boundary · `fix` · T3 · **hazard**

Deletion is bounded to `.claude/`, but `README.md` documents the boundary as `.claude/shared/**`,
`.claude/skills/shared-*/**` and the manifest. A manifest naming downstream-authored `.claude`
content still deletes it.

- **Evidence:** `grep -n "MANAGED_ROOTS = " scripts/sync_payload.py` → `MANAGED_ROOTS = (".claude",)`; compare `README.md` "Ownership boundary". As of `b14d7fa`.
- **Done when:** a manifest naming downstream-authored content inside `.claude/` but outside the documented boundary is refused, **and** legitimate stale cleanup inside the boundary still works, **and** the refusal is non-fatal per the existing skip-and-warn behaviour.
- **Depends on:** BL-01.
- **Found by:** Downstream advocate, deletion-bounds review. **First seen:** 2026-09-06.
- **Status:** open

### BL-03 — a repository that gitignores `.claude/` is reported as a success while receiving nothing · `fix` · T3

`repository_has_changes` sees a clean tree, `process_target` returns "no changes", and the target is
counted among the successes — indefinitely.

- **Evidence:** `grep -n "def repository_has_changes" -A3 scripts/publish.py`; `grep -n "no changes" scripts/publish.py`. As of `b14d7fa`.
- **Why it matters:** a green run that delivered nothing is indistinguishable from a green run that worked.
- **Done when:** a target whose managed paths are ignored is reported distinctly from one that was already up to date, **and** a genuinely unchanged target is still reported as "no changes" rather than as an error.
- **Found by:** Downstream advocate. **First seen:** 2026-09-06.
- **Status:** open

## Workflow security

### BL-04 — the App token is scoped to every repository the owner has · `fix` · T3 · **hazard**

`create-github-app-token` is passed `owner:` with no `repositories:`, so the minted token carries
the App's full permissions across the whole installation rather than the targets being synced.

- **Evidence:** `grep -n "owner:" .github/workflows/sync-instructions.yml`; the action's own docs state that `owner` without `repositories` creates a token for all repositories owned by that owner. As of `b14d7fa`.
- **Why it matters:** `.claude/rules/github-actions.md` requires least privilege, and this token is handed to shell steps.
- **Done when:** the token is scoped to the enabled targets, **and** a target added to `config/targets.json` does not require a second manual edit to become reachable.
- **Found by:** External contract seat. **First seen:** 2026-09-15.
- **Status:** open

### BL-05 — workflow inputs are interpolated directly into `run:` shell · `fix` · T3 · **hazard**

`${{ inputs.version }}` and `${{ github.event.release.tag_name }}` are expanded into shell source in
a step that holds the App token from BL-04.

- **Evidence:** `grep -n 'inputs.version\|tag_name' .github/workflows/sync-instructions.yml`. As of `b14d7fa`.
- **Done when:** both values reach the script through `env:` and are referenced as quoted shell variables, **and** the derived version string is unchanged for a normal release and a normal dispatch.
- **Found by:** External contract seat. **First seen:** 2026-09-15.
- **Status:** open

### BL-06 — pinned actions use mutable major tags rather than commit SHAs · `decision` · T3

A tag repoint by a third party would reach a workflow holding the token from BL-04.

- **Evidence:** `grep -n "uses:" .github/workflows/sync-instructions.yml` → `@v4`, `@v5`, `@v3`. As of `b14d7fa`.
- **Done when:** the owner records a ruling in this entry on SHA-pinning versus tag-pinning, weighing supply-chain risk against the maintenance cost of updating pins. No workflow edit is part of this entry.
- **Found by:** External contract seat. **First seen:** 2026-09-15.
- **Status:** open

### BL-07 — `app-id:` is deprecated in `create-github-app-token@v3` · `fix` · T3

`client-id:` is the current input name. The present form works but emits a deprecation annotation on
every run, and the input name contradicts the variable name it is given.

- **Evidence:** `grep -n "app-id:" .github/workflows/sync-instructions.yml` → fed from `vars.CLAUDE_SYNC_APP_CLIENT_ID`. As of `b14d7fa`.
- **Why T3 despite being one word:** it edits `sync-instructions.yml`, a named T3 trigger, on the authentication path.
- **Done when:** the workflow uses `client-id:`, **and** a dispatch still mints a token successfully.
- **Found by:** External contract seat. **First seen:** 2026-09-15.
- **Status:** open

## Distribution ergonomics

### BL-08 — the PR body does not convey what changed · `fix` · T3

Static apart from `{version}`; says `chore` for behaviour changes; lists no added or removed paths.
A maintainer can receive a PR whose entire content is deletions, titled with a version they already
have.

- **Evidence:** `grep -n "PR_BODY_TEMPLATE" -A20 scripts/publish.py`; `grep -n "chore(ai)" scripts/publish.py`. As of `b14d7fa`.
- **Done when:** the body lists added, modified and removed managed paths for that target, **and** names the profile that produced the selection, **and** a target receiving no changes still opens no PR.
- **Found by:** Downstream advocate, repeatedly across three reviews. **First seen:** 2026-09-06.
- **Status:** open

### BL-09 — there is no downstream-side opt-out · `decision` · T3

`profile` is chosen in this repository by the operator. A target repository cannot decline part of
the payload; its only lever is not merging, and a fresh branch arrives next release.

- **Evidence:** `README.md` "Choosing what a repository is sent" states this explicitly; `grep -n "resolve_selection" scripts/publish.py` shows selection reads nothing from the cloned target. As of `b14d7fa`.
- **Done when:** the owner records a ruling on whether a target may narrow — never widen — its own selection, for instance via a file in the cloned repository. No implementation is part of this entry.
- **Found by:** Downstream advocate. **First seen:** 2026-09-15.
- **Status:** open

### BL-10 — `languages` is parsed and validated but never consulted · `fix` · T2

Both `publish.py` and `validate.py` validate the field; nothing reads it.

- **Evidence:** `grep -rn "languages" scripts/` shows validation and storage only; selection uses `profile` alone. `README.md` already admits it. As of `b14d7fa`.
- **Done when:** either the field affects distribution, **or** it is removed from both validators and from `README.md` — not left as a schema promise nothing keeps.
- **Found by:** Plan checker. **First seen:** 2026-09-15.
- **Status:** open

### BL-11 — `schemaVersion` is written but never read · `fix` · T2

An incompatible future manifest shape will be silently mis-parsed rather than rejected.

- **Evidence:** `grep -rn "schemaVersion" scripts/` → one write in `write_manifest`, no read. As of `b14d7fa`.
- **Done when:** `load_previous_manifest` rejects a manifest whose `schemaVersion` it does not understand, **and** a manifest at the current version still loads, **and** a manifest with no `schemaVersion` is still handled as today.
- **Depends on:** interacts with any manifest-shape change; see the manifest rules in `DEVELOPMENT-LOOP.md`.
- **Found by:** Plan checker. **First seen:** 2026-09-15.
- **Status:** open

## The record

### BL-12 — `VERSION` has not moved for a payload that grew substantially · `decision` · T2

No release has been cut. `AGENTS.md` classifies materially different mandatory downstream agent
behaviour as MAJOR.

- **Evidence:** `cat VERSION` → `0.1.0`; `git tag` → empty. As of `b14d7fa`.
- **Done when:** the owner records a version-impact ruling in this entry. **No `VERSION` edit, tag, or release is part of this entry under any circumstance** — `AGENTS.md` forbids releasing without an explicit request, and publishing a release triggers distribution to every enabled target.
- **Found by:** Downstream advocate. **First seen:** 2026-09-15.
- **Status:** open

### BL-13 — rules stated in more than one payload file · `investigation` · T2

A payload-prose review counted roughly twelve rules appearing in two or more distributed files, with
a proposed canonical location for each. The table itself was not preserved.

- **Evidence:** not preserved — the finding outlived its artifact, which is the failure this file exists to prevent. Re-derive with a duplication pass over `payload/.claude/`, starting from the rules most likely to drift: the floor, no-git-writes, disjointness, controls, tests-must-fail, and the adversarial framing.
- **Done when:** the duplicate set is enumerated with `file:line` for each occurrence and a named canonical copy, recorded **in this entry**. Deduplication itself is a separate entry, because reducing a rule to a pointer may change what an instruction requires, which would make it MAJOR.
- **Found by:** Payload prose seat. **First seen:** 2026-09-15.
- **Status:** open

### BL-14 — "the gates" is used in distributed prose without being defined downstream · `fix` · T2

- **Evidence:** `grep -rn "the gates" payload/`. As of `b14d7fa`.
- **Done when:** each use either names what the gates are for that repository, or defers to the repository's own validation, test and build checks. No distributed instruction refers to an undefined term.
- **Found by:** Payload prose seat. **First seen:** 2026-09-15.
- **Status:** open

## Test coverage

### BL-15 — the symlink refusals on the deletion path have no test on any platform · `fix` · T2

The one symlink test covers the copy path and skips on Windows. The deletion-path guards are
untested everywhere, including on the Linux CI runner.

- **Evidence:** `grep -rn "symlink" tests/` → a single test, decorated `skipUnless(SYMLINKS_SUPPORTED)`, exercising `copy_payload`. As of `b14d7fa`.
- **Done when:** a POSIX-gated test proves a symlinked stale manifest entry is refused rather than followed, **and** it actually executes on the Linux runner rather than skipping there too.
- **Found by:** Diff seat, deletion-bounds review. **First seen:** 2026-09-06.
- **Status:** open

---

## Closed

Closed and declined entries move here with their evidence or reason.

### BL-16 — `validate.py` does not require `DEVELOPMENT-LOOP.md` as a control-plane file · `fix` · T2

It requires `AGENTS.md`, `CLAUDE.md` and `.github/copilot-instructions.md`, but not the procedure
document those two point at.

- **Evidence:** `grep -n "required_files" -A6 scripts/validate.py`. As of `b14d7fa`.
- **Done when:** the file is required and non-empty, **and** a negative test proves the rule can fail, **and** the existing fixture is updated rather than the assertion weakened.
- **Found by:** Plan checker. **First seen:** 2026-09-15.
- **Status:** done — `scripts/validate.py` `validate_control_plane` now lists `DEVELOPMENT-LOOP.md`
  and `BACKLOG.md`; proven by `tests/test_validate.py::test_missing_development_loop_is_rejected`
  and `::test_missing_backlog_is_rejected`, both of which failed before the rule existed.
