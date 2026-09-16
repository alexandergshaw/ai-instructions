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



## Workflow security



### BL-06 — pinned actions use mutable major tags rather than commit SHAs · `decision` · T3

A tag repoint by a third party would reach a workflow holding the token from BL-04.

- **Evidence:** `grep -n "uses:" .github/workflows/sync-instructions.yml` → `@v4`, `@v5`, `@v3`. As of `b14d7fa`.
- **Done when:** the owner records a ruling in this entry on SHA-pinning versus tag-pinning, weighing supply-chain risk against the maintenance cost of updating pins. No workflow edit is part of this entry.
- **Found by:** External contract seat. **First seen:** 2026-09-15.
- **Status:** open


## Distribution ergonomics




## The record

### BL-21 — the payload has moved MAJOR since `v1.0.0` and no release has been cut · `decision` · T2

`checks.md` now defines "The gates" and imposes a **mandatory** obligation on every downstream agent
running the loop: name the exact commands, quote their output, and skip rather than substitute when
the repository defines none. `AGENTS.md` classes materially different mandatory downstream agent
behavior as MAJOR, not MINOR — MINOR covers new **optional** shared instructions.

It does **not** ride the existing tag. `v2.0.0` names a payload snapshot that is already shipped and
sits on an ancestor commit; letting this ride it would make one version string denote two materially
different payloads.

- **Evidence:** `git merge-base --is-ancestor v2.0.0 HEAD` → true, with commits past it;
  `git diff v2.0.0 -- payload/.claude/skills/shared-development-loop/checks.md`.
- **Done when:** the owner rules on the next version string and explicitly requests a release.
  `VERSION` is deliberately unedited and no tag was created: `DEVELOPMENT-LOOP.md` step 7 makes
  release explicit-request-only and never a side effect of finishing a change.
- **Found by:** Classification seat. **First seen:** 2026-09-15.
- **Status:** open

### BL-17 — deduplicate the four rules BL-13 identified · `fix` · T2

Each is stated twice in the payload. A rule in two files drifts — the payload says so itself.

- **Evidence:** the four pairs enumerated in BL-13, with canonical copies named. As of `8553018`.
- **Done when:** each rule is stated once at its canonical location and referenced by path elsewhere, **and** the git-write extension in `shared-development-loop/SKILL.md` (covering `stash`/`checkout`/`restore`/`reset`, which the floor does not) survives the merge, **and** no cross-reference points at a file the reader's profile does not deliver — `tests/test_delivery.py` covers that last one.
- **Why it may be MAJOR:** reducing a rule to a pointer can change what an instruction requires. Re-derive the version impact at step 0. An attempt was classified **PATCH** by the Classification seat on the grounds that every operative rule stayed at point of use and only rationale moved. That ruling stands for the diff it judged; it does not survive the premise problem below.
- **Depends on:** BL-13 (done, and **incomplete** — see below).
- **Attempted 2026-09-15, reverted before commit.** Four seats found the entry's own contract unsound. The attempt is preserved as a patch outside the repository; it is not a base to resume from. Three findings are upstream of the implementation:
  1. **The pointers are unreachable by the dispatch rules in the same skill.** `subagent-execution.md` tells a dispatched seat to "stop and report rather than reach outside" its file allow-list, and read-only seats are given an **empty** one. So converting an inline rule to a cross-file pointer removes it from every scoped seat that is not handed the target file. This objection applies to **all four** deduplications, not to any one of them, and it is the reason the entry cannot be executed as written.
  2. **Rule 4 has a third copy**, at `subagent-execution.md` ("**No git writes.** Not `stash`, `commit`, `checkout`, `restore`, or `reset`"), which `BL-13` did not find. "Stated once at its canonical location" is unreachable while the enumeration names two of three sites.
  3. **There is at least a fifth duplicated rule.** "a failed instrument is invalid, not zero" is in both `SKILL.md` and `traps.md`. The attempt pointered one half of a sentence and left the other half duplicated inline, which reads incoherently — evidence that `BL-13`'s count of four is the wrong contract to build on.
- **Done when (revised):** `BL-13`'s enumeration is re-derived to completion — every duplicated rule, every site, not a sample — **and** the owner rules on finding 1, because a pointer that a scoped seat may not follow is a worse instruction than a duplicate. Deduplication does not proceed before that ruling.
- **Found by:** BL-13 investigation. Premise defects found by the Downstream advocate and Payload prose seats, 2026-09-15.
- **Status:** blocked — needs a decision on finding 1 and a re-run of `BL-13`.

## Test coverage

### BL-19 — no test exercises `process_target` end to end against a real remote · `investigation` · T3

Two defects lived in `process_target` undetected while the suite stayed green: an unbound `subject`
that raised `NameError` on every new-PR path, and a visibility check placed in the wrong branch. The
tests added since stub the network edges — cloning, pushing and the `gh` calls — so anything wrong
in what is actually sent to `gh` still surfaces for the first time during a real distribution run.

- **Evidence:** `grep -n "def _run_process_target" -A12 tests/test_publish.py` shows which edges are
  stubbed. As of the working tree that closed `BL-03`.
- **Why it matters:** this is the function that pushes branches and opens pull requests in
  repositories this project does not own.
- **Done when:** it is recorded whether a dedicated throwaway GitHub repository should carry an
  integration check, or whether the stubbed seam plus the External contract seat is the accepted
  bound. No production, classroom or active repository is used either way.
- **Found by:** Remediation, BL-03 closure. **First seen:** 2026-09-15.
- **Status:** open

### BL-20 — could `validate.py` catch a defined term used in `payload/` without its definition · `investigation` · T2

`BL-14` was closed once while two bare uses of "the gates" remained, and a third sat in
`engineering.md` outside the skill entirely. The payload-prose exemption from writing tests first
was claimed on the grounds that there is no testable surface; a rule of this shape is exactly that
surface.

- **Evidence:** the uses `BL-14` missed on its first pass: `SKILL.md` step 14 and the step 1
  criterion sentence, plus `engineering.md`. As of the working tree that closed `BL-14`.
- **Done when:** it is recorded whether such a rule is worth building — including what it would cost
  in false positives against ordinary English, and whether the term list would be maintained by hand
  — or why it is not. **No rule is built as part of this entry.**
- **Found by:** two review seats, `BL-14` review. **First seen:** 2026-09-15.
- **Status:** open



---

## Closed

Closed and declined entries move here with their evidence or reason.

### BL-09 — there is no downstream-side opt-out · `decision` · T3

`profile` is chosen in this repository by the operator. A target repository cannot decline part of
the payload; its only lever is not merging, and a fresh branch arrives next release.

- **Evidence:** `README.md` "Choosing what a repository is sent" states this explicitly; `grep -n "resolve_selection" scripts/publish.py` shows selection reads nothing from the cloned target. As of `b14d7fa`.
- **Done when:** the owner records a ruling on whether a target may narrow — never widen — its own selection, for instance via a file in the cloned repository. No implementation is part of this entry.
- **Found by:** Downstream advocate. **First seen:** 2026-09-15.
- **Status:** decided — **no.** A target repository may not narrow its own selection. Selection stays wholly in this repository: `enabled` and `profile` in `config/targets.json`, plus the workflow's `targets` input for a single run. The owner's reasoning: one source of truth for what each repository receives. An opt-out file would move that authority into repositories nobody watches, and the drift would arrive silently rather than in review. A target that should not receive something is a `profile` change made here. A downstream maintainer's lever remains declining to merge the pull request — and `BL-08` now makes the pull request say what it would change, which is what makes that lever usable. No implementation follows from this entry; reopening it requires a new entry with a new reason.


### BL-18 — a repository scoped out of successive releases is stranded silently · `fix` · T3

Staged rollout can leave repositories behind indefinitely, and nothing surfaces it. Each downstream
repository records the version it last received, but that value is written and never read: no run
compares it to anything, and no report says which repositories are behind or by how much.

A repository excluded from three consecutive releases produces three green runs and no artifact
anywhere recording that it was skipped.

- **Evidence:** `grep -rn '"version"' scripts/` → one write at `sync_payload.py` `write_manifest`, no read. `grep -rn "skew\|behind\|last received" scripts/` → nothing. The `NOT syncing` line added in `025423e` (`grep -n "NOT syncing" scripts/publish.py`) reports only within a single run and is not retained. As of `025423e`.
- **Why it matters:** scoping was added in `025423e`, so this is now reachable by design rather than by accident. It also compounds `BL-03` — a repository that gitignores `.claude/` is already reported as a success while receiving nothing, and both failures look identical from the central side: a green run and a repository that never got the payload.
- **Not purely central.** From the receiving end there is no signal at all: a skipped repository gets no pull request, so there is no artifact in which "you were excluded" could appear. Its only trace is a manifest `version` string nobody compares.
- **Done when:** a run reports, for **every enabled target including the ones it did not touch**, the version that repository last received — **and** the report is read-only, adding no write, no new token permission, and no file to any downstream repository, **and** a repository whose manifest is absent is reported distinctly from one that is merely behind, since that is the `BL-03` case rather than this one, **and** an unscoped run where every target is current still reports cleanly rather than emitting noise.
- **Suggested shape, not binding:** read `.claude/.central-instructions-manifest.json` from each enabled target through the API the token already permits, decode `version`, and print one line per target. Roughly twenty lines, no new permission. Whether it lives in `publish.py`, a separate script, or a workflow step is open.
- **Depends on:** compounds `BL-03`. Worth doing before staging a rollout across the classroom repositories, because that is when stranding becomes likely rather than theoretical.
- **Found by:** Downstream advocate, rollout-plan review. **First seen:** 2026-09-15.
- **Status:** done — every run reports each enabled target's recorded version, including targets it deliberately skipped. Read-only: it fetches `.claude/.central-instructions-manifest.json` through the API with the token's existing contents-read, writes nothing, and creates no file downstream. A target with no manifest reads distinctly from one merely behind, because those are different failures — the former is `BL-03`.


### BL-11 — `schemaVersion` is written but never read · `fix` · T2

An incompatible future manifest shape will be silently mis-parsed rather than rejected.

- **Evidence:** `grep -rn "schemaVersion" scripts/` → one write in `write_manifest`, no read. As of `b14d7fa`.
- **Done when:** `load_previous_manifest` rejects a manifest whose `schemaVersion` it does not understand, **and** a manifest at the current version still loads, **and** a manifest with no `schemaVersion` is still handled as today.
- **Depends on:** interacts with any manifest-shape change; see the manifest rules in `DEVELOPMENT-LOOP.md`.
- **Found by:** Plan checker. **First seen:** 2026-09-15.
- **Status:** done — `MANIFEST_SCHEMA_VERSION` is now read. A manifest declaring a version this code does not understand authorizes no deletion and warns, but delivery continues and the manifest is rewritten at the known shape — the same self-healing treatment a foreign `source` already gets, rather than a hard failure that would strand the repository. An absent `schemaVersion` behaves as before.


### BL-10 — `languages` is parsed and validated but never consulted · `fix` · T2

Both `publish.py` and `validate.py` validate the field; nothing reads it.

- **Evidence:** `grep -rn "languages" scripts/` shows validation and storage only; selection uses `profile` alone. `README.md` already admits it. As of `b14d7fa`.
- **Done when:** either the field affects distribution, **or** it is removed from both validators and from `README.md` — not left as a schema promise nothing keeps.
- **Found by:** Plan checker. **First seen:** 2026-09-15.
- **Status:** done — removed from the `Target` dataclass, `publish.py` and `validate.py`. A config still setting it is **rejected** with a pointer to profiles rather than silently ignored, because a silently-ignored key is the same broken promise in a quieter form. `README.md` updated. The pre-existing test asserting the old contract was updated to the new one, which is a contract change recorded here rather than a weakened test.


### BL-08 — the PR body does not convey what changed · `fix` · T3

Static apart from `{version}`; says `chore` for behaviour changes; lists no added or removed paths.
A maintainer can receive a PR whose entire content is deletions, titled with a version they already
have.

- **Evidence:** `grep -n "PR_BODY_TEMPLATE" -A20 scripts/publish.py`; `grep -n "chore(ai)" scripts/publish.py`. As of `b14d7fa`.
- **Done when:** the body lists added, modified and removed managed paths for that target, **and** names the profile that produced the selection, **and** a target receiving no changes still opens no PR.
- **Found by:** Downstream advocate, repeatedly across three reviews. **First seen:** 2026-09-06.
- **Correction (2026-09-15):** this closure was partly false. `build_commit_subject` was written but
  never called: `process_target` passed `title=subject` to `create_pr` without ever binding
  `subject`, so **every new-pull-request path raised `NameError`** — and because `NameError` is not
  in the per-target `except` tuple, it aborted the whole run rather than failing one target, against
  `AGENTS.md`'s rule that one downstream failure must not prevent attempts against the rest. The
  name is now bound from the computed `changes` and passed to both `create_pr` and `commit_changes`,
  so the commit subject is used rather than the old static one. The `except` tuple was deliberately
  **not** widened: catching a programming error would hide the next one.
- **Status:** done — `build_pr_body` and `build_commit_subject` describe the specific change: added, updated and removed paths, the profile the target receives, and any path overwritten that no manifest claimed. A first delivery says so rather than calling itself an update, and the body no longer cites a manifest that arrives in the same pull request. The subject distinguishes an install, an update and a removal-only change.


### BL-02 — `MANAGED_ROOTS` is broader than the documented ownership boundary · `fix` · T3 · **hazard**

Deletion is bounded to `.claude/`, but `README.md` documents the boundary as `.claude/shared/**`,
`.claude/skills/shared-*/**` and the manifest. A manifest naming downstream-authored `.claude`
content still deletes it.

- **Evidence:** `grep -n "MANAGED_ROOTS = " scripts/sync_payload.py` → `MANAGED_ROOTS = (".claude",)`; compare `README.md` "Ownership boundary". As of `b14d7fa`.
- **Done when:** a manifest naming downstream-authored content inside `.claude/` but outside the documented boundary is refused, **and** legitimate stale cleanup inside the boundary still works, **and** the refusal is non-fatal per the existing skip-and-warn behaviour.
- **Depends on:** BL-01.
- **Found by:** Downstream advocate, deletion-bounds review. **First seen:** 2026-09-06.
- **Status:** done — `MANAGED_ROOTS = ('.claude',)` replaced by `MANAGED_AREAS`, the boundary `README.md` documents: `.claude/shared/`, `.claude/skills/shared-*/`, and the manifest. Matching is per path component with `*` allowed within one, so every distributed skill is covered and no locally authored one is. Verified against the real payload: a manifest naming `.claude/local/custom.md` and `.claude/skills/local-only/SKILL.md` deletes neither, while a stale `.claude/shared/legacy/old.md` is still removed and delivery continues.


### BL-01 — `copy_payload` overwrites unmanaged downstream files · `fix` · T3 · **hazard**

The copy-side twin of the deletion hole closed in `744d8d2`. `shutil.copy2` runs unconditionally
with no check that the destination pre-existed unmanaged.

- **Evidence:** `grep -n "shutil.copy2" scripts/sync_payload.py` → `shutil.copy2(source, destination)`, as of `b14d7fa`. Reproduced in review: a downstream-authored file inside a skill directory was replaced with no warning.
- **Why it matters:** the payload now ships generically-named files (`roles.md`, `checks.md`) inside skill directories, which makes the collision realistic rather than theoretical.
- **Done when:** an unmanaged downstream file at a payload destination is not silently replaced, **and** a file already recorded in the previous manifest still updates, **and** a first sync after a `source` change still re-adopts every payload file, **and** `tests/test_downstream_safety.py` passes unchanged.
- **Depends on:** coupled with BL-02 — these are the copy and delete halves of one ownership boundary. Fixing either alone leaves the halves inconsistent.
- **Found by:** Diff seat, profiles review. **First seen:** 2026-09-15.
- **Status:** done — overwriting inside the owned area is permitted (that is what ownership means) but never silent: `detect_adoptions` reports every payload destination that already exists downstream and no manifest claimed, and `sync_payload` returns the list and warns per entry. Skipping instead would have broken re-adoption after a `source` change, when the manifest reads as empty and the files are nonetheless ours — covered by `test_re_adoption_after_a_source_change_still_delivers_everything`.


### BL-07 — `app-id:` is deprecated in `create-github-app-token@v3` · `fix` · T3

`client-id:` is the current input name. The present form works but emits a deprecation annotation on
every run, and the input name contradicts the variable name it is given.

- **Evidence:** `grep -n "app-id:" .github/workflows/sync-instructions.yml` → fed from `vars.CLAUDE_SYNC_APP_CLIENT_ID`. As of `b14d7fa`.
- **Why T3 despite being one word:** it edits `sync-instructions.yml`, a named T3 trigger, on the authentication path.
- **Done when:** the workflow uses `client-id:`, **and** a dispatch still mints a token successfully.
- **Found by:** External contract seat. **First seen:** 2026-09-15.
- **Status:** done — `client-id:` replaces `app-id:`. Confirmed at the action's `action.yml` that `app-id` carries `deprecationMessage: "Use 'client-id' instead."`


### BL-05 — workflow inputs are interpolated directly into `run:` shell · `fix` · T3 · **hazard**

`${{ inputs.version }}` and `${{ github.event.release.tag_name }}` are expanded into shell source in
a step that holds the App token from BL-04.

- **Evidence:** `grep -n 'inputs.version\|tag_name' .github/workflows/sync-instructions.yml`. As of `b14d7fa`.
- **Done when:** both values reach the script through `env:` and are referenced as quoted shell variables, **and** the derived version string is unchanged for a normal release and a normal dispatch.
- **Found by:** External contract seat. **First seen:** 2026-09-15.
- **Status:** done — `github.event_name`, `github.event.release.tag_name` and `inputs.version` now reach the script through `env:` and are referenced as quoted shell variables. Verified no `${{ }}` interpolation remains inside any `run:` block.


### BL-04 — the App token is scoped to every repository the owner has · `fix` · T3 · **hazard**

`create-github-app-token` is passed `owner:` with no `repositories:`, so the minted token carries
the App's full permissions across the whole installation rather than the targets being synced.

- **Evidence:** `grep -n "owner:" .github/workflows/sync-instructions.yml`; the action's own docs state that `owner` without `repositories` creates a token for all repositories owned by that owner. As of `b14d7fa`.
- **Why it matters:** `.claude/rules/github-actions.md` requires least privilege, and this token is handed to shell steps.
- **Done when:** the token is scoped to the enabled targets, **and** a target added to `config/targets.json` does not require a second manual edit to become reachable.
- **Found by:** External contract seat. **First seen:** 2026-09-15.
- **Correction (2026-09-15):** this closure was premature. It relied on a comment asserting that an empty
  `repositories` value scopes the token to this repository alone. That is false — the action's README states
  *"If `owner` is set and `repositories` is empty, access will be scoped to all repositories in the provided
  repository owner's installation."* An empty list therefore **widened** the token to the whole installation,
  which is the defect this entry existed to close. Found by two review seats independently; verified at the
  primary source. `scripts/select_targets.py` now refuses to emit an empty list, and the false comment is gone.
- **Status:** done — the workflow now derives the target list from `config/targets.json` and passes it as `repositories:`, with `permission-contents: write`, `permission-pull-requests: write` and `permission-metadata: read`. Verified the derivation yields `instructions-sync-test` alone, and that an empty list falls back to this repository only, which is the safe failure. `repositories` format confirmed at the action's own `action.yml`: comma or newline-separated.


### BL-12 — `VERSION` has not moved for a payload that grew substantially · `decision` · T2

No release has been cut. `AGENTS.md` classifies materially different mandatory downstream agent
behaviour as MAJOR.

- **Evidence:** `cat VERSION` → `0.1.0`; `git tag` → empty. As of `b14d7fa`.
- **Ruling (owner, 2026-09-15):** MAJOR. Released as `v1.0.0`.
- **Found by:** Downstream advocate. **First seen:** 2026-09-15.
- **Status:** done — `VERSION` set to `1.0.0` and tagged `v1.0.0` on explicit request.

### BL-13 — rules stated in more than one payload file · `investigation` · T2

- **Evidence:** re-derived by extracting 7- and 9-word normalised phrases from every file under `payload/.claude/` and intersecting across files. 11 file pairs share verbatim text; **4 are genuine rule duplication**, the rest are a headline-plus-pointer, parallel per-language phrasing, or a skill description restating its own trigger boundary. As of `8553018`.
- **Found:** the earlier review's "roughly twelve" counted shared phrases, not duplicated rules. The actionable set is four:
  1. *"A divergence from the design is not automatically a defect"* — full paragraph at `roles.md:117` and `SKILL.md:189`. **Canonical: `roles.md`**, where the role's behaviour is defined; step 9 should point at it.
  2. The returning-wave spot-check — *"if an agent says it reused an existing helper, grep for it"* — at `subagent-execution.md:141` and `traps.md:46`. **Canonical: `subagent-execution.md`**, which owns dispatch mechanics.
  3. *"a criterion satisfied by a comment containing the right words measures nothing"* at `SKILL.md:49` and `traps.md:9`. **Canonical: `traps.md`**, where it is the named trap "zero-power measurements".
  4. *"a permission configuration that allows a command is not a request to run it"* at `shared-agent-floor/SKILL.md:19` and `shared-development-loop/SKILL.md:60`. **Canonical: the floor.** Note this one is not pure duplication — the loop applies the sentence to `stash`/`checkout`/`restore`/`reset`, which the floor does not cover. Deduplicating it must not drop that extension.
- **Also found, judged not duplication:** the assignment-file-shape guard appears in `repo-structure.md:8`, `SKILL.md` step 8, and the `shared-standardize-repository` description — three statements, but the third is a skill description declaring its own boundary and the second is an application in context. Worth a second opinion rather than a silent merge.
- **Status:** done — findings recorded above. Deduplication itself is `BL-17`, kept separate because reducing a rule to a pointer may change what an instruction requires, which would make it MAJOR.
- **Correction, 2026-09-15:** the enumeration is **incomplete**. `BL-17`'s attempt found a third copy of rule 4 in `subagent-execution.md` and a fifth duplicated rule ("a failed instrument is invalid, not zero", in `SKILL.md` and `traps.md`). The method — intersecting 7- and 9-word normalised phrases — misses a rule restated in different words, which is most of them. Recorded here rather than by reopening the entry, because the finding is about the method and belongs with it.


### BL-16 — `validate.py` does not require `DEVELOPMENT-LOOP.md` as a control-plane file · `fix` · T2

It requires `AGENTS.md`, `CLAUDE.md` and `.github/copilot-instructions.md`, but not the procedure
document those two point at.

- **Evidence:** `grep -n "required_files" -A6 scripts/validate.py`. As of `b14d7fa`.
- **Done when:** the file is required and non-empty, **and** a negative test proves the rule can fail, **and** the existing fixture is updated rather than the assertion weakened.
- **Found by:** Plan checker. **First seen:** 2026-09-15.
- **Status:** done — `scripts/validate.py` `validate_control_plane` now lists `DEVELOPMENT-LOOP.md`
  and `BACKLOG.md`; proven by `tests/test_validate.py::test_missing_development_loop_is_rejected`
  and `::test_missing_backlog_is_rejected`, both of which failed before the rule existed.

### BL-03 — a repository that gitignores `.claude/` is reported as a success while receiving nothing · `fix` · T3

`repository_has_changes` sees a clean tree, `process_target` returns "no changes", and the target is
counted among the successes — indefinitely.

- **Evidence:** `grep -n "def repository_has_changes" -A3 scripts/publish.py`; `grep -n "no changes" scripts/publish.py`. As of `b14d7fa`.
- **Why it matters:** a green run that delivered nothing is indistinguishable from a green run that worked.
- **Done when:** a target whose managed paths are ignored is reported distinctly from one that was already up to date, **and** a genuinely unchanged target is still reported as "no changes" rather than as an error.
- **Found by:** Downstream advocate. **First seen:** 2026-09-06.
- **Status:** done — reported as a **distinct third outcome**, not as a failure. `process_target`
  returns `DeliveredNothing`; `main` prints a "Delivered nothing" bucket separate from successes and
  failures and does not set a non-zero exit code. Failing instead would turn one repository's
  deliberate, documented choice to exclude `.claude/` into a permanently red scheduled job, and a
  job nobody reads hides the next genuine failure — so the bug BL-03 names (counted as a success) is
  closed without trading it for permanent unactionable noise. The check runs unconditionally before
  the clean-tree branch, so the mixed case — one unignored path making the tree dirty — is caught
  too, rather than reaching `git add` and producing git's "use -f" hint against a repository that
  asked for this area not to be committed. Proven by
  `test_a_fully_ignored_target_pushes_nothing_and_opens_no_pull_request`,
  `test_a_partially_ignored_target_is_caught_even_though_the_tree_is_dirty`,
  `test_delivering_nothing_is_a_third_bucket_that_does_not_fail_the_run`, with
  `test_a_target_that_tracks_everything_still_opens_a_pull_request` as the control and
  `test_a_repository_that_tracks_the_managed_area_is_not_flagged` keeping a genuinely unchanged
  target on "no changes".

### BL-14 — "the gates" is used in distributed prose without being defined downstream · `fix` · T2

- **Evidence:** `grep -rn "the gates" payload/`. As of `b14d7fa`.
- **Done when:** each use either names what the gates are for that repository, or defers to the repository's own validation, test and build checks. No distributed instruction refers to an undefined term.
- **Found by:** Payload prose seat. **First seen:** 2026-09-15.
- **Status:** done — `checks.md` defines "The gates" once, as the commands the repository itself
  defines as required, with a first-match-wins source order that says what to do when sources
  disagree and how to scope in a multi-project repository. Every other use points at that file and
  restates nothing (`grep -rn "gates" payload/` → each hit either is in `checks.md` or carries the
  `checks.md` pointer). `engineering.md` is always-on standards prose that the skill may not be
  loaded alongside, so it no longer uses the term at all: it names the checks in plain words and
  depends on no skill file. The "if the repository defines none" clause no longer tells an agent to
  substitute a check — that contradicted the absent-dependency invariant in `SKILL.md` — and now
  says skip and report.

### BL-15 — the symlink refusals on the deletion path have no test on any platform · `fix` · T2

The one symlink test covers the copy path and skips on Windows. The deletion-path guards are
untested everywhere, including on the Linux CI runner.

- **Evidence:** `grep -rn "symlink" tests/` → a single test, decorated `skipUnless(SYMLINKS_SUPPORTED)`, exercising `copy_payload`. As of `b14d7fa`.
- **Done when:** a POSIX-gated test proves a symlinked stale manifest entry is refused rather than followed, **and** it actually executes on the Linux runner rather than skipping there too.
- **Found by:** Diff seat, deletion-bounds review. **First seen:** 2026-09-06.
- **Status:** done — `test_stale_entry_that_is_a_symlink_is_refused_not_followed` and
  `test_stale_entry_under_a_symlinked_parent_is_refused` prove the deletion path refuses rather than
  follows, and `test_symlinks_can_actually_be_created_on_posix` fails on a POSIX runner if symlink
  creation degrades, so these cannot silently become skips on Linux CI. The deletion control is the
  pre-existing `test_removed_managed_file_is_deleted`, with
  `test_stale_file_inside_the_boundary_is_still_deleted` covering the boundary case; a redundant
  control added alongside these tests was dropped rather than duplicating them. Unproven on Windows,
  where these skip by design.
