# GitHub Actions Rule

Applies to: `.github/workflows/**`

- Use least privilege.
- Do not embed secrets.
- Use GitHub App installation authentication for cross-repository access.
- Do not introduce PAT-based authentication without an explicit requirement.
- Do not push directly to downstream default branches.
- Do not automatically merge downstream PRs.
- Preserve manual review.
- Preserve workflow concurrency protections where present.
- Avoid broad permissions such as `write-all`.
