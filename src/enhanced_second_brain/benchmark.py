from __future__ import annotations

import json
import platform
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Settings
from .index import query, rebuild


def run(
    settings: Settings,
    dataset: Path,
    *,
    top_k: int = 5,
    max_p95_ms: float | None = None,
) -> dict[str, Any]:
    cases = json.loads(dataset.read_text(encoding="utf-8"))
    rebuild(settings)
    hits = 0
    latencies = []
    results = []
    for case in cases:
        start = time.perf_counter()
        found = query(settings, case["query"], limit=top_k, track=False)
        elapsed = (time.perf_counter() - start) * 1000
        latencies.append(elapsed)
        paths = [item.path for item in found]
        hit = case["expected"] in paths
        hits += int(hit)
        results.append(
            {
                "query": case["query"],
                "expected": case["expected"],
                "hit": hit,
                "results": paths,
                "latency_ms": round(elapsed, 3),
            }
        )
    p95 = (
        statistics.quantiles(latencies, n=20, method="inclusive")[18]
        if len(latencies) > 1
        else (latencies[0] if latencies else 0.0)
    )
    report = {
        "date": datetime.now(UTC).date().isoformat(),
        "machine": platform.machine(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "cases": len(cases),
        "top_k": top_k,
        "hits": hits,
        "recall": hits / len(cases) if cases else 1.0,
        "p50_ms": round(statistics.median(latencies), 3) if latencies else 0.0,
        "p95_ms": round(p95, 3),
        "results": results,
    }
    report["passed"] = report["recall"] == 1.0 and (
        max_p95_ms is None or p95 <= max_p95_ms
    )
    return report
