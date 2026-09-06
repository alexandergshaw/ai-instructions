from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from sync_payload import MANIFEST_RELATIVE_PATH, SyncError, get_payload_files, load_previous_manifest, sync_payload

REPO_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REQUIRED_ENV_VARS = ("GH_TOKEN", "SOURCE_VERSION", "BOT_NAME", "BOT_EMAIL")
PR_BODY_TEMPLATE = """## Central Claude instruction update

This pull request was generated automatically from the central Claude instructions repository.

**Instruction version:** `{version}`

### Managed content

This automation updates only centrally managed files recorded in:

`.claude/.central-instructions-manifest.json`

Repository-specific Claude instructions and unmanaged `.claude` content are not intentionally modified.

### Review guidance

Review instruction changes before merging, particularly changes to:

- repository structure
- testing behavior
- automated grading
- security rules
- agent workflows
"""


class PublishError(RuntimeError):
    """Raised when publication cannot proceed."""


@dataclass(frozen=True)
class Target:
    repo: str
    enabled: bool = True
    profile: str | None = None
    languages: list[str] | None = None


def run_command(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=merged_env,
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        details = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise PublishError(f"Command failed ({' '.join(command)}): {details}") from exc
    return completed.stdout.strip()


def require_environment() -> dict[str, str]:
    values: dict[str, str] = {}
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise PublishError(f"Missing required environment variables: {', '.join(missing)}")
    for name in REQUIRED_ENV_VARS:
        values[name] = os.environ[name]
    return values


def validate_repo_name(repo: str) -> None:
    if not REPO_NAME_PATTERN.fullmatch(repo):
        raise PublishError(f"Invalid repository name: {repo}")


def load_targets(config_path: Path) -> list[Target]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PublishError("config/targets.json must contain a JSON object.")

    raw_targets = data.get("targets")
    if not isinstance(raw_targets, list):
        raise PublishError("config/targets.json must contain a 'targets' array.")

    targets: list[Target] = []
    seen_repos: set[str] = set()
    for item in raw_targets:
        if not isinstance(item, dict):
            raise PublishError("Each target entry must be an object.")
        repo = item.get("repo")
        enabled = item.get("enabled", True)
        if not isinstance(repo, str):
            raise PublishError("Each target must define a string repo value.")
        validate_repo_name(repo)
        if repo in seen_repos:
            raise PublishError(f"Duplicate target repository: {repo}")
        seen_repos.add(repo)
        if not isinstance(enabled, bool):
            raise PublishError(f"Target {repo} has a non-boolean enabled value.")

        profile = item.get("profile")
        if profile is not None and not isinstance(profile, str):
            raise PublishError(f"Target {repo} has a non-string profile value.")

        languages = item.get("languages")
        if languages is not None and (
            not isinstance(languages, list) or not all(isinstance(language, str) for language in languages)
        ):
            raise PublishError(f"Target {repo} languages must be an array of strings when present.")

        targets.append(
            Target(
                repo=repo,
                enabled=enabled,
                profile=profile,
                languages=languages,
            )
        )
    return targets


def get_default_branch(repo: str, env: dict[str, str]) -> str:
    return run_command(["gh", "api", f"repos/{repo}", "--jq", ".default_branch"], env=env)


def safe_version(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return cleaned or "unknown"


def clone_repository(repo: str, destination: Path, env: dict[str, str]) -> None:
    run_command(["gh", "repo", "clone", repo, str(destination), "--", "--depth", "1"], env=env)


def configure_git_transport_auth(env: dict[str, str]) -> None:
    run_command(["gh", "auth", "setup-git"], env=env)


def branch_ref(branch_name: str) -> str:
    return f"refs/heads/{branch_name}"


def remote_branch_exists(repo_root: Path, branch_name: str, env: dict[str, str]) -> bool:
    merged_env = os.environ.copy()
    merged_env.update(env)
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "origin", branch_ref(branch_name)],
        cwd=repo_root,
        env=merged_env,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 2:
        if not result.stdout.strip() and not result.stderr.strip():
            return False
        details = result.stderr.strip() or result.stdout.strip()
        raise PublishError(f"Failed to inspect remote branch {branch_name}: {details}")

    details = result.stderr.strip() or result.stdout.strip() or "git ls-remote failed"
    raise PublishError(f"Failed to inspect remote branch {branch_name}: {details}")


def configure_git_identity(repo_root: Path, bot_name: str, bot_email: str, env: dict[str, str]) -> None:
    run_command(["git", "config", "user.name", bot_name], cwd=repo_root, env=env)
    run_command(["git", "config", "user.email", bot_email], cwd=repo_root, env=env)


def repository_has_changes(repo_root: Path, env: dict[str, str]) -> bool:
    status = run_command(["git", "status", "--short"], cwd=repo_root, env=env)
    return bool(status)


def checkout_branch(repo_root: Path, branch_name: str, default_branch: str, env: dict[str, str]) -> bool:
    if remote_branch_exists(repo_root, branch_name, env):
        run_command(["git", "fetch", "origin", branch_name], cwd=repo_root, env=env)
        run_command(["git", "checkout", "-B", branch_name, f"origin/{branch_name}"], cwd=repo_root, env=env)
        return True

    run_command(["git", "checkout", "-B", branch_name, default_branch], cwd=repo_root, env=env)
    return False


def commit_changes(repo_root: Path, version: str, managed_paths: list[Path], env: dict[str, str]) -> None:
    unique_paths = sorted({path.as_posix() for path in managed_paths})
    existing_paths = [path for path in unique_paths if (repo_root / path).exists() or (repo_root / path).is_symlink()]
    missing_paths = [path for path in unique_paths if path not in existing_paths]

    if existing_paths:
        run_command(["git", "add", "--", *existing_paths], cwd=repo_root, env=env)
    if missing_paths:
        run_command(["git", "rm", "--quiet", "--ignore-unmatch", "--", *missing_paths], cwd=repo_root, env=env)

    run_command(
        ["git", "commit", "-m", f"chore(ai): update Claude instructions to {version}"],
        cwd=repo_root,
        env=env,
    )


def push_branch(repo_root: Path, branch_name: str, env: dict[str, str], *, force_with_lease: bool) -> None:
    command = ["git", "push"]
    if force_with_lease:
        command.append("--force-with-lease")
    command.extend(["--set-upstream", "origin", f"HEAD:{branch_ref(branch_name)}"])
    run_command(command, cwd=repo_root, env=env)


def find_open_pr(repo: str, branch_name: str, base_branch: str, env: dict[str, str]) -> str | None:
    output = run_command(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--head",
            branch_name,
            "--base",
            base_branch,
            "--state",
            "open",
            "--json",
            "url",
            "--jq",
            ".[0].url // empty",
        ],
        env=env,
    )
    return output or None


def create_pr(repo: str, branch_name: str, base_branch: str, version: str, env: dict[str, str]) -> str:
    title = f"chore(ai): update shared Claude instructions to {version}"
    body = PR_BODY_TEMPLATE.format(version=version)
    return run_command(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo,
            "--base",
            base_branch,
            "--head",
            branch_name,
            "--title",
            title,
            "--body",
            body,
        ],
        env=env,
    )


def process_target(target: Target, source_root: Path, version: str, env: dict[str, str]) -> str:
    validate_repo_name(target.repo)
    default_branch = get_default_branch(target.repo, env)
    branch_name = f"automation/claude-instructions-{safe_version(version)}"

    with tempfile.TemporaryDirectory(prefix="claude-sync-") as temp_dir:
        repo_root = Path(temp_dir) / "target"
        clone_repository(target.repo, repo_root, env)
        configure_git_identity(repo_root, env["BOT_NAME"], env["BOT_EMAIL"], env)
        run_command(["git", "checkout", default_branch], cwd=repo_root, env=env)
        branch_exists = checkout_branch(repo_root, branch_name, default_branch, env)
        previous_manifest = load_previous_manifest(repo_root)
        current_payload_files = get_payload_files(source_root / "payload")
        sync_payload(source_root / "payload", repo_root, version)

        if not repository_has_changes(repo_root, env):
            return f"{target.repo}: no changes"

        managed_paths = [Path(item) for item in previous_manifest.get("files", []) if isinstance(item, str)]
        managed_paths.extend(current_payload_files)
        managed_paths.append(MANIFEST_RELATIVE_PATH)
        commit_changes(repo_root, version, managed_paths, env)
        push_branch(repo_root, branch_name, env, force_with_lease=branch_exists)
        existing_pr = find_open_pr(target.repo, branch_name, default_branch, env)
        if existing_pr:
            return f"{target.repo}: updated existing PR {existing_pr}"

        pr_url = create_pr(target.repo, branch_name, default_branch, version, env)
        return f"{target.repo}: created PR {pr_url}"


def main() -> int:
    source_root = Path(__file__).resolve().parents[1]
    env = require_environment()
    configure_git_transport_auth(env)
    targets = [target for target in load_targets(source_root / "config" / "targets.json") if target.enabled]

    if not targets:
        print("No enabled targets found. Nothing to publish.")
        return 0

    successes: list[str] = []
    failures: list[str] = []
    for target in targets:
        try:
            message = process_target(target, source_root, env["SOURCE_VERSION"], env)
            print(message)
            successes.append(message)
        except (OSError, PublishError, SyncError, json.JSONDecodeError) as exc:
            message = f"{target.repo}: FAILED - {exc}"
            print(message)
            failures.append(message)

    print("\nPublication summary")
    print(f"Successful targets: {len(successes)}")
    for item in successes:
        print(f"- {item}")
    print(f"Failed targets: {len(failures)}")
    for item in failures:
        print(f"- {item}")

    return 1 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublishError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc
