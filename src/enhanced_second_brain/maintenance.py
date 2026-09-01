from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from filelock import FileLock

from .backup import backup
from .config import Settings
from .errors import ESBError
from .index import update
from .okf import audit_vault, migrate_vault
from .prune import apply as apply_prune
from .prune import candidates
from .utility import persist_scores


def state_path(vault: Path) -> Path:
    return vault / "_meta" / "maintenance.json"


def _stamp(now: datetime) -> str:
    return now.astimezone(UTC).isoformat(timespec="seconds")


def _parse(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _fresh(now: datetime) -> dict[str, Any]:
    stamp = _stamp(now)
    return {
        "version": 1,
        "total_turns": 0,
        "turns_since_reconcile": 0,
        "last_reconciled_at": stamp,
        "last_archive_review_at": stamp,
        "last_backup_at": stamp,
    }


def _read(path: Path, now: datetime) -> dict[str, Any]:
    if not path.exists():
        return _fresh(now)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _fresh(now)
    return value if isinstance(value, dict) else _fresh(now)


def _write(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=".maintenance-",
            suffix=".json",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def initialize(settings: Settings, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    path = state_path(settings.vault)
    lock = FileLock(str(path) + ".lock", timeout=30)
    with lock:
        state = _read(path, now)
        _write(path, state)
    return state


def reconcile(settings: Settings) -> dict[str, Any]:
    migration = migrate_vault(settings.vault, write=True)
    audit = audit_vault(settings.vault, strict=True)
    if not audit["valid"]:
        return {"passed": False, "migration": migration, "audit": audit}
    return {
        "passed": True,
        "migration": migration,
        "audit": audit,
        "index": update(settings, verify_hashes=True),
        "utility": persist_scores(settings),
    }


def _elapsed_hours(now: datetime, raw: Any) -> float:
    previous = _parse(raw)
    if previous is None:
        return float("inf")
    return max(0.0, (now - previous.astimezone(UTC)).total_seconds() / 3600)


def run_turn(settings: Settings, *, now: datetime | None = None) -> dict[str, Any]:
    """Advance one agent interaction and perform only due deterministic work."""
    now = now or datetime.now(UTC)
    path = state_path(settings.vault)
    lock = FileLock(str(path) + ".lock", timeout=30)
    with lock:
        state = _read(path, now)
        state["total_turns"] = int(state.get("total_turns", 0)) + 1
        state["turns_since_reconcile"] = int(
            state.get("turns_since_reconcile", 0)
        ) + 1
        reconcile_due = (
            _elapsed_hours(now, state.get("last_reconciled_at"))
            >= settings.maintenance.reconcile_after_hours
            or state["turns_since_reconcile"]
            >= settings.maintenance.reconcile_after_turns
        )
        reconciliation: dict[str, Any] = {"due": reconcile_due, "ran": False}
        if reconcile_due:
            result = reconcile(settings)
            reconciliation.update({"ran": True, "result": result})
            if result.get("passed"):
                state["last_reconciled_at"] = _stamp(now)
                state["turns_since_reconcile"] = 0

        backup_due = settings.backup.enabled and (
            _elapsed_hours(now, state.get("last_backup_at"))
            >= settings.maintenance.backup_after_hours
        )
        backup_result: dict[str, Any] = {"due": backup_due, "ran": False}
        if backup_due:
            try:
                result = backup(settings)
            except (ESBError, OSError) as exc:
                backup_result.update({"ran": True, "error": str(exc)})
            else:
                backup_result.update({"ran": True, "result": result})
                state["last_backup_at"] = _stamp(now)

        archive_due = (
            _elapsed_hours(now, state.get("last_archive_review_at"))
            >= settings.maintenance.archive_review_after_days * 24
        )
        archive_candidates = candidates(settings) if archive_due else []
        if archive_due and not archive_candidates:
            state["last_archive_review_at"] = _stamp(now)
            archive_due = False
        _write(path, state)
    return {
        "turn": state["total_turns"],
        "reconcile": reconciliation,
        "backup": backup_result,
        "archive_review": {
            "due": archive_due,
            "candidates": archive_candidates,
            "instruction": (
                "Read every candidate and its relationships. Preserve rare durable decisions. "
                "Then run maintenance review with only the pages that are truly safe to archive."
                if archive_due
                else None
            ),
        },
    }


def review_archive(
    settings: Settings, paths: list[str], *, now: datetime | None = None
) -> dict[str, Any]:
    """Apply the agent's semantic selection, including an explicit empty selection."""
    now = now or datetime.now(UTC)
    moved = apply_prune(settings, paths) if paths else {"moved": [], "count": 0}
    path = state_path(settings.vault)
    lock = FileLock(str(path) + ".lock", timeout=30)
    with lock:
        state = _read(path, now)
        state["last_archive_review_at"] = _stamp(now)
        _write(path, state)
    return {"reviewed": True, **moved}


def status(settings: Settings, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    state = _read(state_path(settings.vault), now)
    return {
        **state,
        "hours_since_reconcile": round(
            _elapsed_hours(now, state.get("last_reconciled_at")), 2
        ),
        "days_since_archive_review": round(
            _elapsed_hours(now, state.get("last_archive_review_at")) / 24, 2
        ),
    }
