from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import Settings
from .errors import ESBError


def _run(command: list[str]) -> None:
    process = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if process.returncode:
        raise ESBError(
            f"Automation command failed: {' '.join(command)}\n{process.stderr.strip()}"
        )


def _executable() -> str:
    command = shutil.which("esb")
    if not command:
        sibling = Path(sys.executable).with_name(
            "esb.exe" if os.name == "nt" else "esb"
        )
        command = str(sibling) if sibling.exists() else None
    if not command:
        raise ESBError("The esb executable is not available on PATH")
    return str(Path(command).resolve())


def _has_private_backup_target(settings: Settings) -> bool:
    # A Git URL cannot prove that a repository is private. Scheduling a vault
    # push therefore requires an explicit local opt-in.
    if not settings.backup.enabled or not (settings.vault / ".git").exists():
        return False
    process = subprocess.run(
        ["git", "remote", "get-url", settings.backup.remote],
        cwd=settings.vault,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    return process.returncode == 0 and bool(process.stdout.strip())


def _windows(
    settings: Settings, executable: str, *, dry_run: bool, backup_enabled: bool
) -> dict[str, Any]:
    vault = str(settings.vault)
    tasks = [
        (
            "EnhancedSecondBrain-Daily",
            "DAILY",
            "09:00",
            [executable, "--vault", vault, "reconcile"],
        ),
        (
            "EnhancedSecondBrain-MonthlyArchive",
            "MONTHLY",
            "09:15",
            [executable, "--vault", vault, "prune", "apply", "--all-candidates"],
        ),
    ]
    if backup_enabled:
        tasks.append(
            (
                "EnhancedSecondBrain-PrivateBackup",
                "DAILY",
                "21:00",
                [executable, "--vault", vault, "backup"],
            )
        )
    commands = []
    for name, schedule, start, action in tasks:
        task_command = subprocess.list2cmdline(action)
        command = [
            "schtasks",
            "/Create",
            "/F",
            "/TN",
            name,
            "/SC",
            schedule,
            "/ST",
            start,
            "/TR",
            task_command,
        ]
        if schedule == "MONTHLY":
            command.extend(["/D", "1"])
        commands.append(command)
        if not dry_run:
            _run(command)
        settings_script = (
            "$s=New-ScheduledTaskSettingsSet -StartWhenAvailable "
            "-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; "
            f"Set-ScheduledTask -TaskName '{name}' -Settings $s | Out-Null"
        )
        settings_command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            settings_script,
        ]
        commands.append(settings_command)
        if not dry_run:
            _run(settings_command)
    return {
        "platform": "windows",
        "installed": not dry_run,
        "backup_scheduled": backup_enabled,
        "tasks": [name for name, *_ in tasks],
        "commands": commands,
    }


def _macos(
    settings: Settings, executable: str, *, dry_run: bool, backup_enabled: bool
) -> dict[str, Any]:
    target = Path.home() / "Library" / "LaunchAgents"
    specs = {
        "io.enhanced-second-brain.daily": (
            9,
            [executable, "--vault", str(settings.vault), "reconcile"],
        ),
        "io.enhanced-second-brain.monthly-archive": (
            10,
            [
                executable,
                "--vault",
                str(settings.vault),
                "prune",
                "apply",
                "--all-candidates",
            ],
        ),
    }
    if backup_enabled:
        specs["io.enhanced-second-brain.private-backup"] = (
            21,
            [executable, "--vault", str(settings.vault), "backup"],
        )
    written = []
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)
    for label, (hour, arguments) in specs.items():
        plist = target / f"{label}.plist"
        content = _plist(label, arguments, hour, monthly="archive" in label)
        if not dry_run:
            plist.write_text(content, encoding="utf-8", newline="\n")
            uid = str(os.getuid())
            subprocess.run(
                ["launchctl", "bootout", f"gui/{uid}", str(plist)],
                capture_output=True,
                check=False,
            )
            _run(["launchctl", "bootstrap", f"gui/{uid}", str(plist)])
        written.append(str(plist))
    return {
        "platform": "macos",
        "installed": not dry_run,
        "backup_scheduled": backup_enabled,
        "files": written,
    }


def _plist(label: str, arguments: list[str], hour: int, *, monthly: bool) -> str:
    escaped = [
        arg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        for arg in arguments
    ]
    args = "".join(f"<string>{item}</string>" for item in escaped)
    interval = (
        f"<key>Day</key><integer>1</integer><key>Hour</key><integer>{hour}</integer><key>Minute</key><integer>0</integer>"
        if monthly
        else f"<key>Hour</key><integer>{hour}</integer><key>Minute</key><integer>0</integer>"
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>{label}</string>
<key>ProgramArguments</key><array>{args}</array>
<key>StartCalendarInterval</key><dict>{interval}</dict>
</dict></plist>
"""


def _linux(
    settings: Settings, executable: str, *, dry_run: bool, backup_enabled: bool
) -> dict[str, Any]:
    target = Path.home() / ".config" / "systemd" / "user"
    exe = '"' + executable.replace('"', '\\"') + '"'
    vault = '"' + str(settings.vault).replace('"', '\\"') + '"'
    units = {
        "enhanced-second-brain.service": f"[Unit]\nDescription=Reconcile Enhanced Second Brain\n\n[Service]\nType=oneshot\nExecStart={exe} --vault {vault} reconcile\n",
        "enhanced-second-brain.timer": "[Unit]\nDescription=Daily Enhanced Second Brain reconciliation\n\n[Timer]\nOnCalendar=daily\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n",
        "enhanced-second-brain-prune.service": f"[Unit]\nDescription=Archive cold Enhanced Second Brain pages\n\n[Service]\nType=oneshot\nExecStart={exe} --vault {vault} prune apply --all-candidates\n",
        "enhanced-second-brain-prune.timer": "[Unit]\nDescription=Monthly reversible Enhanced Second Brain archival\n\n[Timer]\nOnCalendar=monthly\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n",
    }
    enabled_timers = [
        "enhanced-second-brain.timer",
        "enhanced-second-brain-prune.timer",
    ]
    if backup_enabled:
        units["enhanced-second-brain-backup.service"] = (
            f"[Unit]\nDescription=Back up Enhanced Second Brain\n\n[Service]\nType=oneshot\nExecStart={exe} --vault {vault} backup\n"
        )
        units["enhanced-second-brain-backup.timer"] = (
            "[Unit]\nDescription=Daily private Enhanced Second Brain backup\n\n[Timer]\nOnCalendar=daily\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n"
        )
        enabled_timers.append("enhanced-second-brain-backup.timer")
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)
        for name, content in units.items():
            (target / name).write_text(content, encoding="utf-8", newline="\n")
        _run(["systemctl", "--user", "daemon-reload"])
        _run(["systemctl", "--user", "enable", "--now", *enabled_timers])
    return {
        "platform": "linux",
        "installed": not dry_run,
        "backup_scheduled": backup_enabled,
        "files": [str(target / name) for name in units],
    }


def install_automation(settings: Settings, *, dry_run: bool = False) -> dict[str, Any]:
    executable = _executable()
    system = platform.system().lower()
    backup_enabled = _has_private_backup_target(settings)
    if system == "windows":
        return _windows(
            settings, executable, dry_run=dry_run, backup_enabled=backup_enabled
        )
    if system == "darwin":
        return _macos(
            settings, executable, dry_run=dry_run, backup_enabled=backup_enabled
        )
    if system == "linux":
        return _linux(
            settings, executable, dry_run=dry_run, backup_enabled=backup_enabled
        )
    raise ESBError(f"Automatic scheduling is not supported on {platform.system()}")
