from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .automation import _executable, install_automation
from .config import DEFAULT_TOML, resolve_settings
from .errors import SafetyError
from .index import rebuild
from .maintenance import initialize as initialize_maintenance
from .okf import audit_vault, migrate_vault
from .utility import persist_scores


def _instruction_block(vault: Path, executable: str) -> str:
    command = _agent_command(vault, executable)
    return f"""<!-- enhanced-second-brain:start -->
## Enhanced Second Brain — provider-neutral automatic context

- At the start of every user request, use the context and capture token injected by the native hook. If no hook injected them, send a generic begin event as described below; do not run a separate context lookup first. `{command} context "<the user's exact request>"` remains available for explicit manual lookup. The hook's single context operation advances maintenance, updates FTS5, returns relevant pages and records injections.
- Use the returned context only when relevant. If the command reports maintenance work or an archive review, complete the included instruction before the final answer.
- Read only relevant results with `{command} page read <path>`.
- After using a page in an answer, run `{command} usage record cited <path>`.
- When a hook supplies a capture turn id, assess durable knowledge before the final answer and run `{command} checkpoint complete --turn-id ID --input <temporary-json-file>`, including an empty updates list when nothing should be retained. Search/read existing pages and merge before creating a new page. Keep decisions, resolved incidents, verified results, lasting preferences and reusable lessons; omit trivial exchanges and immediately reconstructible code details.
- Without native hooks, run `{command} hook run --provider generic` with a begin event on stdin (session_id, stable event_id, prompt), follow its context and checkpoint instructions, then send an end event. The installing agent must connect this protocol to its own persistent instructions or hook mechanism. Use `page upsert` for explicit manual edits; touched pages are validated and indexed without full reconciliation.
- If `context` reports an archive review, read every candidate and its relationships. Preserve rare durable decisions even when they are old. Then run `{command} maintenance review [only-the-pages-that-are-truly-safe-to-archive]`; an empty selection records that nothing should move.
- When the user asks for a portable copy, run `{command} reconcile`, then `{command} bundle export <private-destination.zip>` and report its SHA-256.
- The OKF Markdown files are authoritative. FTS5 is a local, disposable search index.
- Keep credentials in `_local/.env` and private documents in `_local/`. Never put their values in notes, prompts, logs, commits or exports. `_local/` is excluded from retrieval, migration and portable bundles; it must also stay Git-ignored. Application-specific local environment files may remain necessary; never publish them.
- This protocol is independent of the model provider. It requires a local agent with filesystem and command access; a browser-only chat cannot access local files by itself.
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


def write_agent_instructions(vault: Path) -> dict[str, Any]:
    changed = []
    executable = _executable()
    if _append_managed(vault / "AGENTS.md", _instruction_block(vault, executable)):
        changed.append("AGENTS.md")
    return {
        "changed": changed,
        "files": ["AGENTS.md"],
        "next_step": (
            "The installing agent should connect this managed block to its own "
            "persistent instruction mechanism."
        ),
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
        "_local/",
        ".env",
        ".env.*",
        "!.env.example",
        "!.env.template",
        "*.pem",
        "*.key",
        "*.p12",
        "*.pfx",
        "_meta/cache/",
        "_meta/usage.jsonl",
        "_meta/usage.jsonl.lock",
        "_meta/utility.json",
        "_meta/maintenance.json",
        "_meta/maintenance.json.lock",
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
    local = vault / "_local"
    if local.is_symlink():
        raise SafetyError("The machine-local credential directory must not be a symlink.")
    local.mkdir(mode=0o700, exist_ok=True)
    (local / "documents").mkdir(mode=0o700, exist_ok=True)
    files = {
        ".env": (
            "# Machine-local credentials: never commit, export or paste into agent prompts.\n"
            "# Add your own NAME=value entries here; no working credentials are provided.\n"
        ),
        "README.md": (
            "# Machine-local storage\n\n"
            "Keep credentials in `.env` and private documents in `documents/`.\n"
            "This directory is excluded from Git, retrieval and portable bundles.\n"
            "Installation never overwrites existing local files.\n"
            "The env file is plain text. Restrict access with your operating system.\n"
            "Applications must explicitly load their required configuration; this file "
            "is not automatically injected into applications or agents.\n"
        ),
    }
    for name, content in files.items():
        try:
            descriptor = os.open(local / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            if os.name == "nt" and name == ".env":
                account = subprocess.check_output(
                    ["whoami"], text=True, stderr=subprocess.DEVNULL
                ).strip()
                subprocess.run(
                    ["icacls", str(local / name), "/inheritance:r", "/grant:r",
                     f"{account}:F", "*S-1-5-18:F", "*S-1-5-32-544:F"],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            stream.write(content)


def install(
    vault: Path,
    *,
    automation: bool = False,
    dry_run_automation: bool = False,
    hooks: bool = True,
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
    agent_instructions = write_agent_instructions(vault)
    result = {
        "passed": True,
        "vault": str(vault),
        "local_credentials": str(vault / "_local" / ".env"),
        "preflight_backup": str(backup_root) if backup_root else None,
        "migration": migration,
        "audit": audit,
        "index": rebuild(settings),
        "utility": persist_scores(settings),
        "maintenance": initialize_maintenance(settings),
        "agent_instructions": agent_instructions,
        "automation": install_automation(settings, dry_run=dry_run_automation)
        if automation
        else {"installed": False, "reason": "disabled"},
    }
    if hooks:
        from .hook_installation import configure

        result["hooks"] = configure(settings)
    else:
        result["hooks"] = {"installed": False, "reason": "disabled"}
    return result
