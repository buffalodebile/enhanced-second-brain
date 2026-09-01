from __future__ import annotations

from typing import Any

from .config import Settings
from .index import query, results_as_dict
from .maintenance import run_turn


def prepare(
    settings: Settings, text: str, *, limit: int | None = None
) -> dict[str, Any]:
    """Prepare one provider-neutral agent turn.

    This is the normal entry point for every local agent: it advances the
    maintenance cadence, incrementally refreshes FTS5, returns likely context,
    and records returned pages as injected.
    """
    maintenance = run_turn(settings)
    context = results_as_dict(query(settings, text, limit=limit, track=True))
    return {
        "query": text,
        "context": context,
        "maintenance": maintenance,
    }
