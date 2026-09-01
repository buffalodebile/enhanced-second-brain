from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from conftest import write_page

from enhanced_second_brain.backup import backup
from enhanced_second_brain.config import Settings
from enhanced_second_brain.errors import SafetyError


def git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=cwd, text=True, encoding="utf-8"
    ).strip()


def test_backup_uses_isolated_index_and_includes_private_ledger(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    remote = tmp_path / "remote.git"
    vault.mkdir()
    subprocess.check_call(["git", "init", "--bare", str(remote)])
    git(vault, "init", "-b", "main")
    git(vault, "config", "user.name", "Synthetic Tester")
    git(vault, "config", "user.email", "synthetic")
    write_page(
        vault, "concepts/base.md", title="Base", description="Base page", body="# Base"
    )
    (vault / ".gitignore").write_text(
        "_meta/usage.jsonl\n_meta/maintenance.json\n", encoding="utf-8"
    )
    git(vault, "add", ".")
    git(vault, "commit", "-m", "initial")
    git(vault, "remote", "add", "origin", str(remote))
    write_page(
        vault,
        "concepts/dirty.md",
        title="Dirty",
        description="Dirty page",
        body="# Dirty",
    )
    ledger = vault / "_meta" / "usage.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        '{"event":"opened","path":"concepts/base.md","weight":1}\n', encoding="utf-8"
    )
    (vault / "_meta" / "maintenance.json").write_text(
        '{"total_turns": 4}\n', encoding="utf-8"
    )
    head_before = git(vault, "rev-parse", "HEAD")
    index_before = git(vault, "write-tree")
    status_before = git(vault, "status", "--porcelain=v1", "--untracked-files=all")
    result = backup(Settings(vault=vault, config_file=None))
    assert result["dirty"] and result["snapshot"]
    assert git(vault, "rev-parse", "HEAD") == head_before
    assert git(vault, "write-tree") == index_before
    assert (
        git(vault, "status", "--porcelain=v1", "--untracked-files=all") == status_before
    )
    snapshot_files = subprocess.check_output(
        [
            "git",
            "--git-dir",
            str(remote),
            "ls-tree",
            "-r",
            "--name-only",
            "backup-snapshot",
        ],
        text=True,
    ).splitlines()
    assert "concepts/dirty.md" in snapshot_files
    assert "_meta/usage.jsonl" in snapshot_files
    assert "_meta/maintenance.json" in snapshot_files


def test_backup_captures_ignored_ledger_without_other_changes(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    remote = tmp_path / "remote.git"
    vault.mkdir()
    subprocess.check_call(["git", "init", "--bare", str(remote)])
    git(vault, "init", "-b", "main")
    git(vault, "config", "user.name", "Synthetic Tester")
    git(vault, "config", "user.email", "synthetic")
    write_page(
        vault, "concepts/base.md", title="Base", description="Base page", body="# Base"
    )
    (vault / ".gitignore").write_text("_meta/usage.jsonl\n", encoding="utf-8")
    git(vault, "add", ".")
    git(vault, "commit", "-m", "initial")
    git(vault, "remote", "add", "origin", str(remote))
    ledger = vault / "_meta" / "usage.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        '{"event":"opened","path":"concepts/base.md","weight":1}\n',
        encoding="utf-8",
    )

    assert git(vault, "status", "--porcelain=v1", "--untracked-files=all") == ""
    first = backup(Settings(vault=vault, config_file=None))
    second = backup(Settings(vault=vault, config_file=None))
    assert first["dirty"] and first["snapshot"]
    assert second["snapshot"] == first["snapshot"]
    assert second["unchanged_snapshot"] is True


@pytest.mark.parametrize("name", ["production.env", "api_key.txt", "id_ed25519"])
def test_backup_refuses_secret_like_untracked_names(tmp_path: Path, name: str) -> None:
    vault = tmp_path / "vault"
    remote = tmp_path / "remote.git"
    vault.mkdir()
    subprocess.check_call(["git", "init", "--bare", str(remote)])
    git(vault, "init", "-b", "main")
    git(vault, "config", "user.name", "Synthetic Tester")
    git(vault, "config", "user.email", "synthetic")
    write_page(
        vault, "concepts/base.md", title="Base", description="Base page", body="# Base"
    )
    git(vault, "add", ".")
    git(vault, "commit", "-m", "initial")
    git(vault, "remote", "add", "origin", str(remote))
    (vault / name).write_text("synthetic placeholder", encoding="utf-8")
    with pytest.raises(SafetyError, match="Secret-like"):
        backup(Settings(vault=vault, config_file=None))
