from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .config import Settings
from .errors import SafetyError
from .okf import audit_vault

SECRET_NAME = re.compile(
    r"(?i)(?:^|[._-])(?:env|credentials?|secrets?|client[-_]?secrets?|"
    r"private[-_]?keys?|"
    r"id_(?:rsa|dsa|ecdsa|ed25519)|api[-_]?keys?|access[-_]?tokens?|"
    r"oauth|tokens?|passwords?)(?:[._-]|$)|\.(?:key|pem|p12|pfx)$"
)


def _git(
    vault: Path, *args: str, env: dict[str, str] | None = None, check: bool = True
) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=vault,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if check and process.returncode:
        raise SafetyError(f"git {' '.join(args)} failed: {process.stderr.strip()}")
    return process.stdout.strip()


def _remote_sha(vault: Path, remote: str, branch: str) -> str | None:
    output = _git(vault, "ls-remote", "--heads", remote, f"refs/heads/{branch}")
    return output.split()[0] if output else None


def _secret_like_untracked(vault: Path) -> list[str]:
    ordinary = _git(vault, "ls-files", "--others", "--exclude-standard", "-z")
    ignored = _git(
        vault, "ls-files", "--others", "--ignored", "--exclude-standard", "-z"
    )
    return sorted(
        {
            path
            for path in (ordinary + "\0" + ignored).split("\0")
            if path and SECRET_NAME.search(Path(path).name)
        }
    )


def backup(settings: Settings) -> dict[str, Any]:
    vault = settings.vault
    if _git(vault, "rev-parse", "--is-inside-work-tree") != "true":
        raise SafetyError("Vault is not a Git worktree")
    audit = audit_vault(vault, strict=True)
    if not audit["valid"]:
        raise SafetyError("Strict OKF audit failed; refusing backup")
    remote = settings.backup.remote
    main = settings.backup.main_branch
    snapshot = settings.backup.snapshot_branch
    head_before = _git(vault, "rev-parse", "HEAD")
    current_branch = _git(vault, "branch", "--show-current")
    if current_branch != main:
        raise SafetyError(
            f"Expected branch {main}, found {current_branch or 'detached HEAD'}"
        )
    _git(vault, "push", remote, f"{head_before}:refs/heads/{main}")
    if _remote_sha(vault, remote, main) != head_before:
        raise SafetyError("Remote main SHA does not match local HEAD")
    private_state = [
        vault / "_meta" / "usage.jsonl",
        vault / "_meta" / "maintenance.json",
    ]
    dirty = (
        bool(_git(vault, "status", "--porcelain=v1", "--untracked-files=all"))
        or any(path.exists() for path in private_state)
    )
    if not dirty:
        return {"main": head_before, "snapshot": None, "dirty": False}
    blocked = _secret_like_untracked(vault)
    if blocked:
        raise SafetyError(
            f"Secret-like untracked filenames refused: {', '.join(blocked)}"
        )
    with tempfile.TemporaryDirectory(prefix="esb-git-index-") as temp_dir:
        index_path = Path(temp_dir) / "index"
        env = dict(os.environ)
        env["GIT_INDEX_FILE"] = str(index_path)
        _git(vault, "read-tree", head_before, env=env)
        _git(vault, "add", "-A", env=env)
        for path in private_state:
            if path.exists():
                _git(vault, "add", "-f", "--", path.relative_to(vault).as_posix(), env=env)
        tree_one = _git(vault, "write-tree", env=env)
        _git(vault, "add", "-A", env=env)
        for path in private_state:
            if path.exists():
                _git(vault, "add", "-f", "--", path.relative_to(vault).as_posix(), env=env)
        tree_two = _git(vault, "write-tree", env=env)
        if tree_one != tree_two:
            raise SafetyError("Worktree changed while building the snapshot")
        if _git(vault, "rev-parse", "HEAD") != head_before:
            raise SafetyError("HEAD changed while building the snapshot")
        old = _remote_sha(vault, remote, snapshot)
        if old:
            _git(
                vault,
                "fetch",
                "--no-tags",
                "--no-write-fetch-head",
                remote,
                f"refs/heads/{snapshot}",
            )
            old_tree = _git(vault, "rev-parse", f"{old}^{{tree}}")
            if old_tree == tree_one:
                return {
                    "main": head_before,
                    "snapshot": old,
                    "dirty": True,
                    "previous_snapshot": old,
                    "unchanged_snapshot": True,
                }
        commit = _git(
            vault,
            "commit-tree",
            tree_one,
            "-p",
            head_before,
            "-m",
            "backup: isolated working tree snapshot",
            env=env,
        )
    old = _remote_sha(vault, remote, snapshot)
    lease = f"--force-with-lease=refs/heads/{snapshot}:{old or ''}"
    _git(vault, "push", lease, remote, f"{commit}:refs/heads/{snapshot}")
    if _remote_sha(vault, remote, snapshot) != commit:
        raise SafetyError("Remote snapshot SHA does not match the isolated commit")
    return {
        "main": head_before,
        "snapshot": commit,
        "dirty": True,
        "previous_snapshot": old,
    }
