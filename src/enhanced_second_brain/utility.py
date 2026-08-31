from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from typing import Any

from .config import Settings
from .graph import backlinks
from .pages import iter_page_paths, parse_markdown
from .usage import aggregate


def _parse_date(value: Any, fallback: datetime) -> datetime:
    if not value:
        return fallback
    raw = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return fallback


def scores(settings: Settings, *, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(UTC)
    usage = aggregate(settings)
    incoming = backlinks(settings.vault)
    tier_weight = {"core": 1.0, "supporting": 0.65, "peripheral": 0.35}
    rows = []
    for path in iter_page_paths(settings.vault):
        page = parse_markdown(path, settings.vault)
        stat_date = datetime.fromtimestamp(path.stat().st_mtime, UTC)
        updated = _parse_date(page.metadata.get("updated"), stat_date)
        age_days = max(0.0, (now - updated).total_seconds() / 86400)
        recent = math.exp(-math.log(2) * age_days / 180)
        effective = float(usage.get(page.relative_path, {}).get("effective_usage", 0.0))
        usage_factor = min(1.0, math.log1p(effective) / math.log(11))
        importance = min(
            1.0,
            0.5 * tier_weight.get(str(page.metadata.get("tier", "supporting")), 0.65)
            + 0.3 * float(page.metadata.get("base_confidence", 0.5))
            + 0.2 * min(1.0, incoming.get(page.relative_path, 0) / 5),
        )
        strength = importance * (0.6 * recent + 0.4 * usage_factor)
        rows.append(
            {
                "path": page.relative_path,
                "strength": round(strength, 6),
                "effective_usage": effective,
                "last_used": usage.get(page.relative_path, {}).get("last_used"),
                "age_days": round(age_days, 1),
                "backlinks": incoming.get(page.relative_path, 0),
            }
        )
    return sorted(rows, key=lambda row: (row["strength"], row["path"]))


def persist_scores(
    settings: Settings, *, now: datetime | None = None
) -> dict[str, Any]:
    rows = scores(settings, now=now)
    destination = settings.vault / "_meta" / "utility.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": (now or datetime.now(UTC)).isoformat(timespec="seconds"),
        "pages": rows,
    }
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"path": str(destination), "pages": len(rows)}
