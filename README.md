# claude-instructions

Central source of truth for shared Claude Code instructions, reusable skills, and downstream synchronization automation.

## Purpose

This repository owns centrally managed Claude instruction content that is versioned, validated, and distributed to downstream repositories through reviewable pull requests. It is intended to keep shared AI engineering standards consistent without taking ownership of repository-specific Claude files.

## Architecture

```text
Central repository
      ↓
Versioned release
      ↓
GitHub App authenticated workflow
      ↓
Target repositories
      ↓
Automation branch
      ↓
Pull request
      ↓
Human review + merge
```

The distributed payload lives under `payload/.claude/` in this repository and is copied into downstream repositories under `.claude/`.


## Repository-local AI instructions

`AGENTS.md` is the canonical cross-agent guidance for working on this repository itself.

- `CLAUDE.md` is a thin Claude adapter that points to `AGENTS.md`.
- `.github/copilot-instructions.md` is a thin GitHub Copilot adapter that points to `AGENTS.md`.
- `.claude/rules/**` contains Claude-specific scoped rules for working on particular areas of this central repository.

None of these control-plane files are automatically included in the downstream distributed payload under `payload/`.

## Ownership boundary

Central repo owns:

```text
.claude/shared/**
.claude/skills/shared-*/**
.claude/.central-instructions-manifest.json
```

Target repositories own:

```text
CLAUDE.md
.claude content not listed in the central manifest
project/application files
```

The sync process never intentionally modifies a downstream root `CLAUDE.md`, and it only removes files that were previously recorded in the central manifest and are no longer present in the current payload.

## Repository layout

```text
.github/workflows/
config/targets.json
payload/.claude/shared/**
payload/.claude/skills/shared-*/**
scripts/
tests/
VERSION
```

## Adding a downstream repository

1. Install the GitHub App on the target repository.
2. Add the target repository to `config/targets.json`.
3. Set `"enabled": true` for that repository.
4. Run the manual sync workflow with `workflow_dispatch`.
5. Review the generated downstream pull request.
6. Add or update the target repository's `CLAUDE.md` imports as needed.

The target schema is intentionally small today:

```json
{
  "targets": [
    {
      "repo": "YOUR-GITHUB-OWNER/example-repository",
      "enabled": false
    }
  ]
}
```

## Choosing what a repository is sent

This is the **central operator's** control, and deliberately only that. A target repository
cannot decline part of the payload; what it can do is not merge the pull request, and that
pull request now states exactly what it would add, change and remove.

Selection has one source of truth: `enabled` and `profile` here, plus the workflow's `targets`
input for a single run. A downstream-side opt-out file was considered and **declined** — it would
move the decision about what a repository receives into fifty repositories nobody reviews.

A target with no `profile` receives the whole payload. Naming a profile limits it:

```json
{
  "targets": [
    { "repo": "OWNER/intro-cs-assignments", "enabled": true, "profile": "standards-only" }
  ]
}
```

Profiles live in `config/profiles.json` and are lists of payload path prefixes:

```json
{
  "profiles": {
    "standards-only": [".claude/shared/languages/", ".claude/shared/testing/"]
  }
}
```

**Prefixes match whole path components.** A prefix ending in `/` selects a directory and
everything beneath it; any other prefix must equal a payload path exactly. So
`.claude/shared/core/` selects that directory, while `.claude/shared/core/eng` selects nothing
and is rejected rather than quietly matching `engineering.md`.

**Some payload paths ship regardless of profile.** `REQUIRED_PAYLOAD_PATHS` in
`scripts/sync_payload.py` lists them, and today it holds two skill directories: `shared-agent-floor`,
the rules bounding what an agent may do without being asked, and `shared-development-loop`, the
staged development process. Entries use the same matching rule as a selection prefix. A profile
cannot exclude them, and validation fails if a required path matches no file.

Both travel as skills because `.claude/skills/` is discovered on its own, while `.claude/shared/**`
only loads where a downstream `CLAUDE.md` imports it — which most target repositories do not have.

Two profiles ship by default. `standards-only` sends the shared engineering, language and testing
rules, plus the two required skills. `autograded` adds the autograder and standardization skills on
top of those. Neither can exclude the required skills — the development loop is the heaviest thing
in the payload, and it is delivered everywhere, because a process that reaches only some
repositories is not a process.

**Narrowing a profile removes files downstream.** The excluded files were recorded in that
repository's manifest, so the next sync deletes them — the intended way to withdraw something from
a repository that should not have received it. Unmanaged downstream files are untouched, as always.

Validation rejects **each** prefix that selects nothing, not merely a profile that selects nothing
in total. That matters because a profile with five good prefixes and one typo would otherwise pass
CI and silently delete every file the dead prefix used to cover. A prefix also goes dead when a
payload directory is renamed, so this check guards releases as well as edits.

A target that still sets `languages` is rejected, with a pointer to profiles. The field never
affected distribution, and language selection is expressible as a profile — two mechanisms for
one job is how they drift apart.

## Sending a release to some repositories but not others

`enabled` decides whether a repository is ever synced and `profile` decides what it receives.
Neither scopes a single run — a publish reaches every enabled target.

The **Sync Claude Instructions** workflow takes an optional `targets` input for that:

```text
targets:  (blank)                              every enabled target
          instructions-sync-test, python       only those two
```

Scoping only narrows. A name that is unknown, disabled, or ambiguous between two configured
owners **fails the run before anything is cloned** — a typo must not quietly turn a fleet-wide
publish into a no-op. Matching is exact on the repository name or on `owner/name`, never a
prefix, so `python` does not drag in `python-course`.

The run prints the repositories it will sync and the enabled ones it is deliberately skipping,
before the first clone.

**The App token scopes to the run, not to the fleet.** `scripts/select_targets.py` computes the
list once and both the workflow's token step and `publish.py` use it, so a canary run cannot hold
a credential for the repositories it is not touching. That script refuses to emit an empty list:
the token action documents that an empty `repositories` with `owner` set grants access to every
repository in the installation, so an empty value widens scope rather than narrowing it.

A published **release is never scoped** — it reaches every enabled target. Staged rollout is a
`workflow_dispatch` activity.

## GitHub App setup

Do not use a PAT. The sync workflow is designed for short-lived GitHub App installation tokens created at runtime.

Required GitHub App permissions:

```text
Contents: Read and write
Pull requests: Read and write
Metadata: Read-only
```

Central repository configuration:

Variables:

```text
CLAUDE_SYNC_APP_CLIENT_ID
CLAUDE_SYNC_INSTALLATION_OWNER
```

Secret:

```text
CLAUDE_SYNC_APP_PRIVATE_KEY
```

The repository `GITHUB_TOKEN` is used only for reading this repository during workflow execution. Cross-repository changes use the GitHub App token.

## Manual publication

Use the **Sync Claude Instructions** workflow with `workflow_dispatch`.

Inputs:

- `ref` (required, default `main`): the Git ref to publish from for testing.
- `version` (optional): the version label to include in branch names, manifests, commit messages, and pull requests.

If `version` is omitted, the workflow derives a value like `manual-<short-sha>`.

## Production publication

Production publication is triggered by a published GitHub Release. The release tag is treated as the authoritative `SOURCE_VERSION`.

Typical flow:

```text
commit
→ tag
→ GitHub Release
→ release published
→ automatic downstream PR creation
```

Example commands:

```bash
git tag v1.0.0
git push origin v1.0.0
```

After pushing the tag, publish a GitHub Release for that tag to trigger downstream synchronization.

## Versioning

Use semantic versioning guidance for shared instruction changes.

PATCH examples:

- typo fixes
- clarification
- non-behavioral documentation updates

MINOR examples:

- new optional instruction
- new language rule
- new shared skill

MAJOR examples:

- repository structure changes
- test structure changes
- grading behavior changes
- major behavioral changes to shared Claude instructions

## Rollback

If a distributed change should be undone, downstream repositories can revert the synchronization pull request, or this repository can publish a corrective follow-up version.

## Security

- Do not use a PAT.
- Do not store downstream credentials in this repository.
- Use short-lived GitHub App installation tokens.
- Install the GitHub App only on repositories that should be managed.
- Use least privilege for the GitHub App.
- Do not enable automatic merges initially.

## Failure behavior

- One downstream failure does not prevent attempts against other enabled targets.
- The publication workflow still fails overall if any target repository fails.
- Re-running the same version is intended to be safe and idempotent.

## Local validation

Run the repository checks locally with:

```bash
python scripts/validate.py
python -m unittest discover -s tests -v
```

These checks validate configuration structure, payload safety rules, and manifest-based synchronization behavior.
