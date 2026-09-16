from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from select_targets import SelectionError, excluded_targets, parse_requested, select_targets
from sync_payload import MANIFEST_RELATIVE_PATH, SyncError, get_payload_files, load_previous_manifest, sync_payload

REPO_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REQUIRED_ENV_VARS = ("GH_TOKEN", "SOURCE_VERSION", "BOT_NAME", "BOT_EMAIL")
_UNUSED_PR_BODY_TEMPLATE = """## Central Claude instruction update

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
class DeliveredNothing:
    """A target that was reached and left holding nothing, because git will not record it.

    Neither a success nor a failure. Counting it among the successes is the BL-03 bug. Failing
    the run instead would turn one repository's deliberate, documented choice to exclude
    `.claude/` into a permanently red scheduled job, which is a different way of being unread.
    """

    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class Target:
    repo: str
    enabled: bool = True
    profile: str | None = None


def _render_paths(heading: str, paths: list[str]) -> str:
    if not paths:
        return ""
    listed = "\n".join(f"- `{path}`" for path in sorted(paths))
    return f"### {heading}\n\n{listed}\n\n"


def build_pr_body(
    *,
    version: str,
    profile: str | None,
    added: list[str],
    modified: list[str],
    removed: list[str],
    adopted: list[str],
) -> str:
    """Describe this specific change, not the automation in general.

    A body that is identical every time tells a reviewer nothing, and on a first delivery the
    old template pointed at a manifest that arrives in the same pull request -- so the one
    document it offered as evidence could not be consulted.
    """
    first_delivery = not modified and not removed and bool(added)
    opening = (
        "This is the **first** delivery of centrally managed instructions to this repository."
        if first_delivery
        else "This updates centrally managed instruction files in this repository."
    )
    scope = f"`{profile}`" if profile else "the complete instruction set"

    sections = (
        _render_paths("Added", added)
        + _render_paths("Updated", modified)
        + _render_paths("Removed", removed)
    )
    if removed:
        sections += (
            "Removed files were recorded in this repository's manifest and are no longer part of "
            "the central set. Files this repository authored are never removed.\n\n"
        )
    if adopted:
        listed = "\n".join(f"- `{path}`" for path in sorted(adopted))
        sections += (
            "### Overwritten without a prior record\n\n"
            "These paths already existed here and no manifest claimed them. They sit inside the "
            "area the central repository owns, so the write proceeded -- it is listed rather than "
            f"silent so you can check it:\n\n{listed}\n\n"
        )

    return (
        f"## Instruction update — `{version}`\n\n"
        f"{opening}\n\n"
        f"**Receiving:** {scope}\n\n"
        f"{sections}"
        "### What this automation does and does not touch\n\n"
        "It manages only the paths listed in `.claude/.central-instructions-manifest.json` after "
        "this pull request lands. Your root `CLAUDE.md`, and any `.claude` content this repository "
        "authored outside the central area, are never modified or removed.\n\n"
        "### Review guidance\n\n"
        "These files instruct AI agents working in this repository, so a change here changes how "
        "they behave. Worth a closer look: repository structure, testing behaviour, automated "
        "grading, security rules, and anything that authorizes an agent to act without asking.\n"
    )


def build_commit_subject(
    version: str, *, added: list[str], modified: list[str], removed: list[str]
) -> str:
    """A subject that distinguishes an install from an update from a removal."""
    if added and not modified and not removed:
        return f"chore(ai): add shared agent instructions ({version})"
    if removed and not added and not modified:
        return f"chore(ai): remove {len(removed)} retired agent instruction file(s) ({version})"
    parts = []
    if added:
        parts.append(f"+{len(added)}")
    if modified:
        parts.append(f"~{len(modified)}")
    if removed:
        parts.append(f"-{len(removed)}")
    return f"chore(ai): update shared agent instructions ({version}, {' '.join(parts)})"


def classify_changes(repo_root: Path, env: dict[str, str]) -> dict[str, list[str]]:
    """Read the working tree to find what this sync actually did."""
    status = run_command(["git", "status", "--porcelain"], cwd=repo_root, env=env)
    changes: dict[str, list[str]] = {"added": [], "modified": [], "removed": []}
    for line in status.splitlines():
        if not line.strip():
            continue
        code, _, path = line.strip().partition(" ")
        path = path.strip().strip('"')
        if code.startswith("D"):
            changes["removed"].append(path)
        elif code.startswith("?") or code.startswith("A"):
            changes["added"].append(path)
        else:
            changes["modified"].append(path)
    return changes


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

        if "languages" in item:
            raise PublishError(
                f"Target {repo} sets 'languages', which no longer affects distribution. "
                "Express language selection as a profile in config/profiles.json instead."
            )

        targets.append(
            Target(
                repo=repo,
                enabled=enabled,
                profile=profile,
            )
        )
    return targets


def format_fleet_report(versions: dict[str, str | None], *, current_version: str) -> list[str]:
    """One line per enabled target, including the ones this run did not touch."""
    lines = ["Fleet status"]
    for repo in sorted(versions):
        recorded = versions[repo]
        if recorded is None:
            lines.append(
                f"  {repo}: no manifest — has never received a delivery, or is not committing "
                "the managed area"
            )
        elif recorded == current_version:
            lines.append(f"  {repo}: {recorded}")
        else:
            lines.append(f"  {repo}: {recorded} — behind {current_version}")
    return lines


def read_recorded_version(repo: str, env: dict[str, str]) -> str | None:
    """Read a target's recorded version without cloning it. Read-only; writes nothing."""
    try:
        encoded = run_command(
            [
                "gh", "api", f"repos/{repo}/contents/{MANIFEST_RELATIVE_PATH.as_posix()}",
                "--jq", ".content",
            ],
            env=env,
        )
    except PublishError:
        return None
    try:
        document = json.loads(base64.b64decode(encoded).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    version = document.get("version")
    return version if isinstance(version, str) else None


def load_profiles(config_path: Path) -> dict[str, tuple[str, ...]]:
    """Read config/profiles.json. Absent means every target receives the whole payload."""
    if not config_path.exists():
        return {}

    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PublishError("config/profiles.json must contain a JSON object.")

    raw_profiles = data.get("profiles")
    if not isinstance(raw_profiles, dict):
        raise PublishError("config/profiles.json must contain a 'profiles' object.")

    profiles: dict[str, tuple[str, ...]] = {}
    for name, prefixes in raw_profiles.items():
        if not isinstance(prefixes, list) or not all(isinstance(item, str) for item in prefixes):
            raise PublishError(f"Profile {name} must be an array of path prefixes.")
        if not prefixes:
            raise PublishError(f"Profile {name} must list at least one path prefix.")
        profiles[name] = tuple(prefixes)
    return profiles


def resolve_selection(
    target: Target, profiles: dict[str, tuple[str, ...]]
) -> tuple[str, ...] | None:
    """Return the payload prefixes this target receives, or None for the whole payload."""
    if target.profile is None:
        return None
    if target.profile not in profiles:
        raise PublishError(f"Target {target.repo} names an unknown profile: {target.profile}")
    return profiles[target.profile]


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


def ignored_managed_paths(repo_root: Path, paths: list[Path], env: dict[str, str]) -> list[str]:
    """Managed paths that exist on disk but that git refuses to track.

    `git check-ignore` exits 1 when nothing matches, which is a normal answer rather than a
    failure, so this cannot go through `run_command` -- that treats any non-zero exit as fatal.
    """
    candidates = sorted({path.as_posix() for path in paths if (repo_root / path).exists()})
    if not candidates:
        return []

    merged_env = os.environ.copy()
    merged_env.update(env)
    completed = subprocess.run(
        ["git", "check-ignore", "--"] + candidates,
        cwd=repo_root,
        env=merged_env,
        text=True,
        capture_output=True,
    )
    if completed.returncode not in (0, 1):
        # An unreadable answer is not evidence that nothing is ignored. Say so rather than
        # returning an empty list, which would read as "all clear".
        raise PublishError(
            f"Could not determine whether the managed area is ignored: "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def report_invisible_delivery(
    repo_root: Path, paths: list[Path], env: dict[str, str]
) -> str | None:
    """Describe the managed paths git will never record, or None when every path is trackable.

    A repository that excludes `.claude/` receives every file on disk and commits none of them.
    The working tree is clean, so that looks identical to "already up to date" -- and the target
    is counted among the successes on every run thereafter while holding nothing.

    The reader of this text is the operator of *this* repository, reading a workflow log. No
    pull request is created, so nobody downstream ever sees it: it says what happened and which
    lever this reader actually holds, rather than instructing an absent party to edit a file in
    a repository they do not own.
    """
    ignored = ignored_managed_paths(repo_root, paths, env)
    if not ignored:
        return None

    considered = sorted({path.as_posix() for path in paths})
    listed = ", ".join(ignored)
    return (
        f"{len(ignored)} of {len(considered)} managed path(s) are matched by this repository's "
        f"exclude rules, so git cannot record them and nothing was committed: {listed}. "
        "The remaining paths were not delivered either, because the delivery is not split. "
        "This is the downstream repository's own choice to make; the lever here is whether the "
        "target stays in config/targets.json."
    )


def checkout_branch(repo_root: Path, branch_name: str, default_branch: str, env: dict[str, str]) -> bool:
    if remote_branch_exists(repo_root, branch_name, env):
        run_command(["git", "fetch", "origin", branch_name], cwd=repo_root, env=env)
        run_command(["git", "checkout", "-B", branch_name, f"origin/{branch_name}"], cwd=repo_root, env=env)
        return True

    run_command(["git", "checkout", "-B", branch_name, default_branch], cwd=repo_root, env=env)
    return False


def commit_changes(repo_root: Path, version: str, managed_paths: list[Path], env: dict[str, str], subject: str | None = None) -> None:
    unique_paths = sorted({path.as_posix() for path in managed_paths})
    existing_paths = [path for path in unique_paths if (repo_root / path).exists() or (repo_root / path).is_symlink()]
    missing_paths = [path for path in unique_paths if path not in existing_paths]

    if existing_paths:
        run_command(["git", "add", "--", *existing_paths], cwd=repo_root, env=env)
    if missing_paths:
        run_command(["git", "rm", "--quiet", "--ignore-unmatch", "--", *missing_paths], cwd=repo_root, env=env)

    message = subject or f"chore(ai): update Claude instructions to {version}"
    run_command(
        ["git", "commit", "-m", message],
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


def create_pr(repo: str, branch_name: str, base_branch: str, version: str, env: dict[str, str], title: str | None = None, body: str | None = None) -> str:
    title = title or f"chore(ai): update shared agent instructions ({version})"
    body = body or ""
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


def process_target(
    target: Target,
    source_root: Path,
    version: str,
    env: dict[str, str],
    profiles: dict[str, tuple[str, ...]] | None = None,
) -> str | DeliveredNothing:
    validate_repo_name(target.repo)
    selection = resolve_selection(target, profiles or {})
    default_branch = get_default_branch(target.repo, env)
    branch_name = f"automation/claude-instructions-{safe_version(version)}"

    with tempfile.TemporaryDirectory(prefix="claude-sync-") as temp_dir:
        repo_root = Path(temp_dir) / "target"
        clone_repository(target.repo, repo_root, env)
        configure_git_identity(repo_root, env["BOT_NAME"], env["BOT_EMAIL"], env)
        run_command(["git", "checkout", default_branch], cwd=repo_root, env=env)
        branch_exists = checkout_branch(repo_root, branch_name, default_branch, env)
        previous_manifest = load_previous_manifest(repo_root)
        current_payload_files = get_payload_files(source_root / "payload", selection)
        adopted = sync_payload(source_root / "payload", repo_root, version, selection)
        changes = classify_changes(repo_root, env)

        managed_paths = [Path(item) for item in previous_manifest.get("files", []) if isinstance(item, str)]
        managed_paths.extend(current_payload_files)
        managed_paths.append(MANIFEST_RELATIVE_PATH)

        # Unconditionally, before the clean-tree branch. A single unignored path -- the manifest
        # is enough -- makes the tree dirty, and inside the clean-tree branch this check would
        # never run for exactly the mixed case it exists to catch: `git add` would then be handed
        # an explicitly named excluded path and fail with git's "use -f" hint, which must never
        # be followed against a repository that asked for this area not to be committed.
        # The previous manifest's paths are included because an excluded *deletion* is equally
        # invisible.
        invisible = report_invisible_delivery(repo_root, managed_paths, env)
        if invisible is not None:
            return DeliveredNothing(f"{target.repo}: delivered nothing — {invisible}")

        if not repository_has_changes(repo_root, env):
            return f"{target.repo}: no changes"

        subject = build_commit_subject(
            version,
            added=changes["added"],
            modified=changes["modified"],
            removed=changes["removed"],
        )
        commit_changes(repo_root, version, managed_paths, env, subject=subject)
        push_branch(repo_root, branch_name, env, force_with_lease=branch_exists)
        existing_pr = find_open_pr(target.repo, branch_name, default_branch, env)
        if existing_pr:
            return f"{target.repo}: updated existing PR {existing_pr}"

        pr_url = create_pr(
            target.repo,
            branch_name,
            default_branch,
            version,
            env,
            title=subject,
            body=build_pr_body(
                version=version,
                profile=target.profile,
                added=changes["added"],
                modified=changes["modified"],
                removed=changes["removed"],
                adopted=adopted,
            ),
        )
        return f"{target.repo}: created PR {pr_url}"


def main() -> int:
    source_root = Path(__file__).resolve().parents[1]
    env = require_environment()
    configure_git_transport_auth(env)
    config_path = source_root / "config" / "targets.json"
    try:
        # Read the configuration once. Deriving the selection from a second, separate read of the
        # same file is how the run's targets and the token's scope drift apart.
        configured = load_targets(config_path)
        config = {
            "targets": [
                {"repo": target.repo, "enabled": target.enabled} for target in configured
            ]
        }
        requested = parse_requested(os.environ.get("REQUESTED_TARGETS"))
        chosen = select_targets(config, requested)
    except (PublishError, SelectionError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1

    chosen_repos = {entry["repo"] for entry in chosen}
    targets = [target for target in configured if target.enabled and target.repo in chosen_repos]

    # Print the resolved scope before the first clone. An operator must be able to read back what
    # the run decided, not what they meant.
    print(f"Scope: {'named targets' if requested else 'every enabled target'}")
    for target in targets:
        print(f"  will sync   {target.repo}")
    for repo in excluded_targets(config, chosen):
        print(f"  NOT syncing {repo} (enabled, excluded from this run)")
    print()
    profiles = load_profiles(source_root / "config" / "profiles.json")

    if not targets:
        print("No enabled targets found. Nothing to publish.")
        return 0

    successes: list[str] = []
    failures: list[str] = []
    delivered_nothing: list[str] = []
    for target in targets:
        try:
            outcome = process_target(target, source_root, env["SOURCE_VERSION"], env, profiles)
            print(outcome)
            if isinstance(outcome, DeliveredNothing):
                delivered_nothing.append(str(outcome))
            else:
                successes.append(str(outcome))
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
    # A third bucket, not a success and not a failure. It must be visible -- that is BL-03 --
    # without turning a downstream team's documented choice into a permanently red job.
    print(f"Delivered nothing: {len(delivered_nothing)}")
    for item in delivered_nothing:
        print(f"- {item}")

    return 1 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublishError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc
