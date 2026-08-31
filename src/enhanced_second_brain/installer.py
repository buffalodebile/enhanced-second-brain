from __future__ import annotations

import json
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

INSTRUCTION_BLOCK = """<!-- enhanced-second-brain:start -->
## Enhanced Second Brain — automatic context

- Before answering any request that may concern prior work, decisions, preferences, projects, or internal names, run `esb index query "<the user's question>"` from this vault.
- Read only relevant results with `esb page read <path>`. Use `esb graph` only for paths, dependencies, hubs, clusters, bridges, or multi-hop questions.
- After using a page in an answer, run `esb usage record cited <path>`.
- After creating durable knowledge, use `esb page upsert` and run `esb reconcile`.
- Markdown/Enhanced OKF is authoritative. The FTS5 cache is local and reconstructible. Do not use QMD, embeddings, a GPU service, or a vector daemon.
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
- Read only relevant results with `{command} page read <path>`. Use graph commands only for structural or multi-hop questions.
- After using a page in an answer, run `{command} usage record cited <path>`.
- After creating durable knowledge, use `{command} page upsert` and run `{command} reconcile`.
- Markdown/Enhanced OKF is authoritative. The FTS5 cache is local and reconstructible. Do not require a skill, QMD, embeddings, a GPU process, or a vector daemon.
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


def install_agent_integrations(
    vault: Path, *, codex_home: Path | None = None
) -> dict[str, Any]:
    changed = []
    conflicts = []
    for relative in ("AGENTS.md", "CLAUDE.md"):
        if _append_managed(vault / relative, INSTRUCTION_BLOCK):
            changed.append(relative)
    executable = _executable()
    codex = vault / ".codex" / "config.toml"
    mcp_block = f"""# enhanced-second-brain:start
[mcp_servers.enhanced-second-brain]
command = {json.dumps(executable)}
args = ["--vault", {json.dumps(str(vault))}, "mcp"]
cwd = {json.dumps(str(vault))}
required = false
default_tools_approval_mode = "writes"
# enhanced-second-brain:end
"""
    existing_codex = codex.read_text(encoding="utf-8") if codex.exists() else ""
    if (
        "[mcp_servers.enhanced-second-brain]" in existing_codex
        and "# enhanced-second-brain:start" not in existing_codex
    ):
        conflicts.append(
            ".codex/config.toml already defines mcp_servers.enhanced-second-brain"
        )
    elif _append_managed(
        codex,
        mcp_block,
        start="# enhanced-second-brain:start",
        end="# enhanced-second-brain:end",
    ):
        changed.append(".codex/config.toml")

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
        "conflicts": conflicts,
        "files": [
            "AGENTS.md",
            "CLAUDE.md",
            ".codex/config.toml",
            str(global_target),
        ],
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
    integrations = install_agent_integrations(vault, codex_home=codex_home)
    result = {
        "passed": True,
        "vault": str(vault),
        "preflight_backup": str(backup_root) if backup_root else None,
        "migration": migration,
        "audit": audit,
        "index": rebuild(settings),
        "utility": persist_scores(settings),
        "agent_integrations": integrations,
        "automation": install_automation(settings, dry_run=dry_run_automation)
        if automation
        else {"installed": False, "reason": "disabled"},
    }
    return result
