from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
import math
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


def aggregate(
    settings: Settings, *, now: datetime | None = None, half_life_days: int = 180
) -> dict[str, dict[str, Any]]:
    now = now or datetime.now(UTC)
    result: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "effective_usage": 0.0,
            "decayed_effective_usage": 0.0,
            "events": 0,
            "last_used": None,
        }
    )
    for item in events(settings.vault):
        row = result[item["path"]]
        weight = float(item.get("weight", settings.usage.weights[item["event"]]))
        row["effective_usage"] += weight
        row["events"] += 1
        timestamp = item.get("at")
        parsed = None
        if timestamp:
            try:
                parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
            except ValueError:
                parsed = None
        if parsed is not None:
            age_days = max(0.0, (now - parsed.astimezone(UTC)).total_seconds() / 86400)
            row["decayed_effective_usage"] += weight * math.exp(
                -math.log(2) * age_days / half_life_days
            )
        if timestamp and (row["last_used"] is None or timestamp > row["last_used"]):
            row["last_used"] = timestamp
    return {
        path: {
            **row,
            "effective_usage": round(row["effective_usage"], 6),
            "decayed_effective_usage": round(
                row["decayed_effective_usage"], 6
            ),
        }
        for path, row in result.items()
    }
