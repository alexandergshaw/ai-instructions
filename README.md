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

It is structured so that future optional fields such as `profile` or `languages` can be added without redesigning the automation.

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
