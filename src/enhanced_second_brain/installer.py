from __future__ import annotations

import os
import shlex
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .automation import _executable, install_automation
from .config import DEFAULT_TOML, resolve_settings
from .index import rebuild
from .okf import audit_vault, migrate_vault
from .utility import persist_scores


def _instruction_block(vault: Path, executable: str) -> str:
    command = _agent_command(vault, executable)
    return f"""<!-- enhanced-second-brain:start -->
## Enhanced Second Brain — automatic context

- Before answering any request that may concern prior work, decisions, preferences, projects, or internal names, run `{command} index query "<the user's question>"`.
- Read only relevant results with `{command} page read <path>`.
- After using a page in an answer, run `{command} usage record cited <path>`.
- After creating durable knowledge, use `{command} page upsert` and run `{command} reconcile`.
- Markdown/Enhanced OKF is authoritative. FTS5 is a local reconstructible cache. Do not add QMD, embeddings, a GPU service, a vector daemon, a graph service, or MCP.
<!-- enhanced-second-brain:end -->
"""


def _agent_command(
    vault: str | Path, executable: str, *, windows: bool | None = None
) -> str:
    windows = os.name == "nt" if windows is None else windows
    if windows:

        def quote(value: str | Path) -> str:
            return "'" + str(value).replace("'", "''") + "'"

        return f"& {quote(executable)} --vault {quote(vault)}"
    return f"{shlex.quote(executable)} --vault {shlex.quote(str(vault))}"


def _global_instruction_block(vault: Path, executable: str) -> str:
    command = _agent_command(vault, executable)
    return f"""<!-- enhanced-second-brain-global:start -->
## Enhanced Second Brain — automatic global context

- Before answering any request that may concern prior work, decisions, preferences, projects, or internal names, run `{command} index query "<the user's question>"`.
- Read only relevant results with `{command} page read <path>`.
- After using a page in an answer, run `{command} usage record cited <path>`.
- After creating durable knowledge, use `{command} page upsert` and run `{command} reconcile`.
- Markdown/Enhanced OKF is authoritative. FTS5 is a local reconstructible cache. Do not require a skill, QMD, embeddings, a GPU process, a vector daemon, a graph service, or MCP.
<!-- enhanced-second-brain-global:end -->
"""


def _append_managed(
    path: Path,
    block: str,
    *,
    start: str = "<!-- enhanced-second-brain:start -->",
    end: str = "<!-- enhanced-second-brain:end -->",
) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if start in current and end in current:
        prefix = current.split(start, 1)[0].rstrip()
        suffix = current.split(end, 1)[1].lstrip("\r\n")
        desired = (prefix + "\n\n" if prefix else "") + block.rstrip() + "\n" + suffix
    else:
        desired = current.rstrip() + ("\n\n" if current.strip() else "") + block
    if desired == current:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desired, encoding="utf-8", newline="\n")
    return True


def connect_ai(vault: Path, *, codex_home: Path | None = None) -> dict[str, Any]:
    changed = []
    executable = _executable()
    if _append_managed(vault / "AGENTS.md", _instruction_block(vault, executable)):
        changed.append("AGENTS.md")
    if codex_home is None:
        configured_home = os.environ.get("CODEX_HOME")
        codex_home = (
            Path(configured_home).expanduser()
            if configured_home
            else Path.home() / ".codex"
        )
    override = codex_home / "AGENTS.override.md"
    global_target = (
        override
        if override.exists() and override.read_text(encoding="utf-8").strip()
        else codex_home / "AGENTS.md"
    )
    if _append_managed(
        global_target,
        _global_instruction_block(vault, executable),
        start="<!-- enhanced-second-brain-global:start -->",
        end="<!-- enhanced-second-brain-global:end -->",
    ):
        changed.append(str(global_target))
    return {
        "changed": changed,
        "files": ["AGENTS.md", str(global_target)],
    }


def _initialize(vault: Path) -> None:
    vault.mkdir(parents=True, exist_ok=True)
    for directory in (
        "concepts",
        "projects",
        "references",
        "_meta/cache",
        "_archives/pruned",
    ):
        (vault / directory).mkdir(parents=True, exist_ok=True)
    config = vault / "second-brain.toml"
    if not config.exists():
        config.write_text(DEFAULT_TOML, encoding="utf-8", newline="\n")
    ignore = vault / ".gitignore"
    additions = [
        "_meta/cache/",
        "_meta/usage.jsonl",
        "_meta/usage.jsonl.lock",
        "_meta/utility.json",
    ]
    existing = (
        ignore.read_text(encoding="utf-8").splitlines() if ignore.exists() else []
    )
    ignore.write_text(
        "\n".join(existing + [line for line in additions if line not in existing])
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def install(
    vault: Path,
    *,
    automation: bool = True,
    dry_run_automation: bool = False,
    codex_home: Path | None = None,
) -> dict[str, Any]:
    vault = vault.expanduser().resolve()
    _initialize(vault)
    preview = migrate_vault(vault, write=False)
    backup_root = None
    if preview["changed"]:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_root = vault / "_archives" / "install-preflight" / stamp
        for relative in preview["changed"]:
            source = vault / relative
            destination = backup_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    migration = migrate_vault(vault, write=True)
    settings = resolve_settings(vault)
    audit = audit_vault(vault, strict=True)
    if not audit["valid"]:
        return {
            "passed": False,
            "vault": str(vault),
            "backup": str(backup_root) if backup_root else None,
            "audit": audit,
        }
    ai_connection = connect_ai(vault, codex_home=codex_home)
    result = {
        "passed": True,
        "vault": str(vault),
        "preflight_backup": str(backup_root) if backup_root else None,
        "migration": migration,
        "audit": audit,
        "index": rebuild(settings),
        "utility": persist_scores(settings),
        "ai_connection": ai_connection,
        "automation": install_automation(settings, dry_run=dry_run_automation)
        if automation
        else {"installed": False, "reason": "disabled"},
    }
    return result
