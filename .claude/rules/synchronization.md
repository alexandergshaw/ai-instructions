# Synchronization Rule

Applies to: `scripts/**`, `tests/**`, `config/**`

- Synchronization must remain idempotent.
- Never delete unmanaged files.
- Only delete files previously recorded in the managed manifest.
- Preserve downstream root `CLAUDE.md`.
- Preserve unmanaged downstream skills, rules, and configuration.
- Filesystem behavior requires tests.
- One target failure should not prevent attempts against remaining targets.
- Use temporary directories for tests.
- Avoid network dependencies in unit tests.
- Do not weaken validation merely to make tests pass.
