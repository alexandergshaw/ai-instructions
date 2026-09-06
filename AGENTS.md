# Agent Instructions

## Repository Purpose

This repository is the central source of truth and distribution system for shared AI-agent instructions used across downstream repositories.

Treat the repository as two different layers:

### Control-plane files

These operate this central repository itself and are not distributed downstream unless a future requirement explicitly says otherwise.

Examples:

```text
AGENTS.md
CLAUDE.md
DEVELOPMENT-LOOP.md
.github/**
.claude/**
config/**
scripts/**
tests/**
pyproject.toml
README.md
VERSION
```

### Distributed payload

Everything under `payload/` is intended to be copied into downstream repositories.

Example:

```text
payload/.claude/shared/core/engineering.md
```

becomes:

```text
.claude/shared/core/engineering.md
```

inside a downstream repository.

Keep this distinction explicit in every change.

## Working Procedure

This document defines policy: what must be true, and who owns what. `DEVELOPMENT-LOOP.md`
defines procedure: what to do, in what order, and what must be proven before a change is
complete.

Follow `DEVELOPMENT-LOOP.md` for every change. It classifies work into three tiers by blast
radius and states the gates required at each. Where the two documents appear to conflict, this
one governs.

## Critical Ownership Boundary

- Root `AGENTS.md` defines how repository-aware coding agents work on this repository.
- Root `CLAUDE.md` is the Claude-specific adapter for this repository.
- `.github/copilot-instructions.md` is the Copilot-specific adapter for this repository.
- Local `.claude/rules/**` files govern Claude while working on this repository.
- Files under `payload/` define behavior intended for downstream repositories.

Rules:

- Never place root `AGENTS.md` into `payload/` unless explicitly requested.
- Never place root `CLAUDE.md` into `payload/` unless explicitly requested.
- Never automatically distribute `.github/copilot-instructions.md`.
- Never assume local `.claude/rules/**` should be copied downstream.
- Do not duplicate central-repo-only behavior inside downstream payload instructions.
- Do not modify downstream root `CLAUDE.md` as part of normal synchronization.

## Source-of-Truth Map

| Concern | Source of truth |
| --- | --- |
| How agents work on this repository | `AGENTS.md` |
| Development procedure and change tiers | `DEVELOPMENT-LOOP.md` |
| Claude adapter for this repository | `CLAUDE.md` |
| Copilot adapter for this repository | `.github/copilot-instructions.md` |
| Repo-specific Claude rules | `.claude/rules/**` |
| Target repositories | `config/targets.json` |
| Distributed files | `payload/` |
| Synchronization behavior | `scripts/sync_payload.py` |
| Publishing behavior | `scripts/publish.py` |
| Validation rules | `scripts/validate.py` |
| Expected behavior | `tests/` |
| CI validation | `.github/workflows/validate.yml` |
| Distribution workflow | `.github/workflows/sync-instructions.yml` |
| Human-facing documentation | `README.md` |

## Change Classification

### Central-system change

Examples: synchronization behavior, publishing behavior, GitHub Actions, target configuration, manifest handling, validation, tests, and release tooling.

These belong in control-plane files.

### Shared-instruction change

Examples: engineering standards, language rules, testing behavior, autograding rules, reusable skills, and downstream Claude instructions.

These belong under `payload/`.

### Both

Some tasks affect both layers. Example: profile-based selective distribution may require changes in `config/`, `scripts/`, `tests/`, and `README.md` while also changing how `payload/` content is selected.

Rules:

- Do not modify payload files merely because control-plane implementation changes.
- Do not modify synchronization code merely because wording in one distributed instruction changes.
- Preserve the separation unless the task genuinely crosses both layers.

## Modification Rules

- Inspect the existing implementation before introducing new abstractions.
- Prefer the smallest correct change.
- Avoid unrelated refactoring.
- Preserve existing public behavior unless requirements explicitly change it.
- Preserve synchronization idempotency.
- Never use destructive synchronization against the entire downstream `.claude` directory.
- Only remove downstream files previously recorded as centrally managed.
- Never delete unmanaged downstream `.claude` content.
- Never modify downstream root `CLAUDE.md` during normal synchronization.
- Never push directly to downstream default branches.
- Never automatically merge downstream PRs unless explicitly requested.
- Never replace GitHub App authentication with a PAT unless explicitly required.
- Never commit credentials, tokens, private keys, or `.env` files.
- A failure against one downstream repository must not prevent attempts against remaining repositories.
- Keep changes scoped to the requested task.
- Inspect diffs before considering work complete.

## Downstream Repository Safety

- Do not modify real downstream repositories while developing or testing this central system unless explicitly requested.
- Prefer unit tests with temporary local filesystem structures.
- Use a dedicated test repository for GitHub integration testing.
- Never use production, classroom, or active development repositories as implicit test fixtures.
- Do not trigger releases or distribution workflows during ordinary development unless explicitly requested.

## Validation Requirements

### After Python or synchronization changes

1. Run the unit tests.
2. Run `python scripts/validate.py` if it exists.
3. Inspect `git diff`.
4. Confirm unmanaged downstream files remain protected.
5. Confirm synchronization remains idempotent.
6. Confirm tests exist for new filesystem behavior.

### After changes under `payload/`

1. Run validation.
2. Run the test suite.
3. Inspect the payload diff.
4. Determine whether the change is PATCH, MINOR, or MAJOR.
5. Do not publish a release unless explicitly requested.

### After GitHub Actions changes

1. Inspect workflow permissions.
2. Preserve least privilege.
3. Confirm secrets are referenced rather than embedded.
4. Confirm downstream authentication still uses the GitHub App.
5. Confirm workflows do not push directly to protected or default branches.

## Versioning Guidance

### PATCH

- typo fixes
- wording clarifications
- non-behavioral documentation changes

### MINOR

- new optional shared instructions
- new language guidance
- new skills
- backwards-compatible capabilities

### MAJOR

- repository structure changes
- testing convention changes
- autograding behavior changes
- synchronization semantic changes
- materially different mandatory downstream agent behavior

Do not update `VERSION`, create tags, create releases, or trigger production distribution unless the task explicitly requires release preparation or publication.

## Agent Compatibility

Keep the central architecture vendor-neutral wherever practical so shared policy can eventually support Claude Code, GitHub Copilot, OpenAI Codex, and other repository-aware coding agents.

- Do not assume all downstream consumers use Claude.
- Keep shared concepts vendor-neutral where practical.
- Place vendor-specific configuration in vendor-specific adapters or payload locations.
- Avoid duplicating shared policy across vendors.
- Prefer one canonical source plus thin adapters or generated representations.
- Do not rename generic concepts to Claude-specific names unless the concept truly is Claude-specific.
