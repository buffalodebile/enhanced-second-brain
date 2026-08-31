from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from filelock import FileLock

from .config import Settings
from .errors import ValidationError
from .pages import is_knowledge_path, safe_relative

EVENTS = {"injected", "opened", "cited"}


def ledger_path(vault: Path) -> Path:
    return vault / "_meta" / "usage.jsonl"


def record(
    settings: Settings, event: str, path: str | Path, *, at: str | None = None
) -> dict[str, Any]:
    if event not in EVENTS:
        raise ValidationError(f"Unknown usage event: {event}")
    resolved, relative = safe_relative(settings.vault, path, must_exist=True)
    if not is_knowledge_path(settings.vault, resolved):
        raise ValidationError("Usage can only be recorded for knowledge Markdown pages")
    ledger = ledger_path(settings.vault)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "at": at or datetime.now(UTC).isoformat(timespec="seconds"),
        "event": event,
        "path": relative,
        "weight": settings.usage.weights[event],
    }
    lock = FileLock(str(ledger) + ".lock", timeout=10)
    with lock, ledger.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
    return payload


def events(vault: Path) -> list[dict[str, Any]]:
    ledger = ledger_path(vault)
    if not ledger.exists():
        return []
    parsed: list[dict[str, Any]] = []
    with ledger.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
                if item.get("event") in EVENTS and item.get("path"):
                    parsed.append(item)
            except json.JSONDecodeError:
                continue
    return parsed


def aggregate(settings: Settings) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"effective_usage": 0.0, "events": 0, "last_used": None}
    )
    for item in events(settings.vault):
        row = result[item["path"]]
        row["effective_usage"] += float(
            item.get("weight", settings.usage.weights[item["event"]])
        )
        row["events"] += 1
        timestamp = item.get("at")
        if timestamp and (row["last_used"] is None or timestamp > row["last_used"]):
            row["last_used"] = timestamp
    return dict(result)
