# Payload Rule

Applies to: `payload/**`

- Files under `payload/` are intended for downstream repositories.
- Treat these files as shared, public configuration and instructions.
- Do not include assumptions that only apply to the central repository.
- Do not reference central-only paths such as `scripts/` or `config/` unless the distributed instruction specifically requires that knowledge.
- Avoid repository-specific assumptions.
- Consider downstream compatibility before changing shared behavior.
- Payload changes may affect many repositories.
- Do not publish or release automatically.
