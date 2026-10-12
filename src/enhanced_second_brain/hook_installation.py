"""Idempotent native configuration; never changes provider trust settings."""

from __future__ import annotations

import os
import shlex
import shutil
import copy
import tomllib
from pathlib import Path
from typing import Any

from filelock import FileLock
from filelock import Timeout

from .atomic import read_json, write_json
from .automation import _executable
from .checkpoints import digest
from .config import Settings
from .errors import ValidationError

PROVIDERS = ("codex", "claude")
EVENTS = ("UserPromptSubmit", "Stop", "SessionEnd")


def _home() -> Path:
    return Path.home()


def _root(provider: str) -> Path:
    variable = "CODEX_HOME" if provider == "codex" else "CLAUDE_CONFIG_DIR"
    return Path(os.environ.get(variable) or (_home() / (".codex" if provider == "codex" else ".claude"))).expanduser()


def _config(provider: str) -> Path:
    return _root(provider) / ("hooks.json" if provider == "codex" else "settings.json")


def _detected(provider: str) -> bool:
    return _root(provider).exists() or shutil.which(provider) is not None


def _owned(handler: dict, installation_id: str) -> bool:
    args = handler.get("args")
    if isinstance(args, list):
        return any(args[i:i + 2] == ["--installation-id", installation_id] for i in range(len(args) - 1))
    return f"--installation-id {installation_id}" in str(handler.get("command", ""))


def _handler(settings: Settings, provider: str, installation_id: str) -> dict[str, Any]:
    executable = _executable()
    args = ["--vault", str(settings.vault), "hook", "run", "--provider", provider,
            "--installation-id", installation_id]
    if provider == "claude":
        # Exec form avoids all shell interpolation, including Windows paths with spaces.
        return {"type": "command", "command": executable, "args": args, "timeout": 30}
    command = " ".join(shlex.quote(arg) for arg in [executable, *args])
    handler: dict[str, Any] = {"type": "command", "command": command, "timeout": 30}
    if os.name == "nt":
        # Codex's Windows override invokes its shell; single-quoted PowerShell
        # literals are carried in an encoded command to keep paths shell-safe.
        import base64

        literal = lambda value: "'" + value.replace("'", "''") + "'"
        script = "& " + " ".join(literal(arg) for arg in [executable, *args]) + "; exit $LASTEXITCODE"
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        handler["commandWindows"] = f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {encoded}"
    return handler


def _read(path: Path) -> dict[str, Any]:
    config = read_json(path, {})
    if not isinstance(config, dict) or not isinstance(config.get("hooks", {}), dict):
        raise ValidationError("Agent config must be an object with a hooks object")
    for groups in config.get("hooks", {}).values():
        if not isinstance(groups, list) or any(
            not isinstance(group, dict) or not isinstance(group.get("hooks"), list)
            or any(not isinstance(handler, dict) for handler in group["hooks"])
            for group in groups
        ):
            raise ValidationError("Existing hook configuration is malformed; it was not changed")
    return config


def _count(config: dict, installation_id: str) -> dict[str, int]:
    return {event: sum(_owned(handler, installation_id)
                       for group in config.get("hooks", {}).get(event, [])
                       for handler in group["hooks"]) for event in EVENTS}


def status(settings: Settings, provider: str = "auto") -> dict[str, Any]:
    if provider not in (*PROVIDERS, "auto"):
        raise ValidationError("Unsupported hook provider")
    installation_id = digest(str(settings.vault.resolve()))[:24]
    result = {}
    for name in PROVIDERS if provider == "auto" else (provider,):
        path = _config(name)
        try:
            config = _read(path)
            counts = _count(config, installation_id)
            configured = all(count == 1 for count in counts.values())
            error = None
        except (ValueError, OSError, ValidationError):
            configured = False
            counts = {}
            error = "Unreadable or malformed native hook configuration"
        detected = _detected(name)
        # Presence doesn't establish runtime capability or activation. The native
        # application owns review and can disable global hooks through its policies.
        enabled = config.get("disableAllHooks") is not True if error is None else False
        managed_only = False
        if name == "codex" and (_root(name) / "config.toml").exists():
            try:
                with (_root(name) / "config.toml").open("rb") as stream:
                    data = tomllib.load(stream)
                managed_only = data.get("hooks", {}).get("allow_managed_hooks_only", False)
            except (OSError, ValueError):
                pass
        result[name] = {
            "detected": detected, "config": str(path), "configured": configured,
            "events": counts, "capability": "runtime_verification_required" if detected else "not_detected",
            "activation": ("disabled_by_native_config" if not enabled or managed_only else
                           "native_review_required" if configured and name == "codex" else
                           "runtime_verification_required" if configured else "not_configured"),
            "error": error,
        }
    return {"providers": result}


def configure(settings: Settings, provider: str = "auto", *, uninstall: bool = False) -> dict[str, Any]:
    if provider not in (*PROVIDERS, "auto"):
        raise ValidationError("Unsupported hook provider")
    installation_id = digest(str(settings.vault.resolve()))[:24]
    changed = []
    errors = {}
    for name in PROVIDERS if provider == "auto" else (provider,):
        if provider == "auto" and not _detected(name):
            continue
        path = _config(name)
        if uninstall and not path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with FileLock(str(path) + ".esb.lock", timeout=5):
                config = _read(path)
                before = copy.deepcopy(config)
                hooks = config.setdefault("hooks", {})
                for event in EVENTS:
                    groups = []
                    for group in hooks.get(event, []):
                        handlers = [item for item in group["hooks"] if not _owned(item, installation_id)]
                        if handlers or not group["hooks"]:
                            groups.append({**group, "hooks": handlers})
                    if not uninstall:
                        groups.append({"hooks": [_handler(settings, name, installation_id)]})
                    if groups:
                        hooks[event] = groups
                    else:
                        hooks.pop(event, None)
                if config != before:
                    write_json(path, config)
                    changed.append(name)
        except (OSError, ValueError, ValidationError, Timeout):
            errors[name] = "Native config was not changed; repair its syntax or file permissions"
    return {"changed": changed, "errors": errors, **status(settings, provider),
            "notice": "Review new or changed Codex hooks with /hooks in Codex; trust is never bypassed."}
