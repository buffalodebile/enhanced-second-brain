from __future__ import annotations

import subprocess
from pathlib import Path

from enhanced_second_brain.automation import _has_private_backup_target, _plist
from enhanced_second_brain.config import BackupConfig, Settings


def test_backup_schedule_requires_explicit_opt_in(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    subprocess.check_call(["git", "init", str(vault)])
    subprocess.check_call(
        ["git", "-C", str(vault), "remote", "add", "origin", "synthetic://remote"]
    )
    disabled = Settings(vault=vault, config_file=None)
    enabled = Settings(vault=vault, config_file=None, backup=BackupConfig(enabled=True))
    assert _has_private_backup_target(disabled) is False
    assert _has_private_backup_target(enabled) is True


def test_macos_archival_does_not_run_at_install_time() -> None:
    content = _plist(
        "io.enhanced-second-brain.archive",
        ["esb", "prune", "apply", "--all-candidates"],
        9,
        monthly=True,
    )
    assert "RunAtLoad" not in content
