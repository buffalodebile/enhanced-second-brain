"""Reproducible synthetic comparison: FTS5 versus reading every Markdown file."""

from __future__ import annotations

import argparse
import json
import platform
import re
import statistics
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from enhanced_second_brain.config import Settings
from enhanced_second_brain.index import query, rebuild
from enhanced_second_brain.pages import iter_page_paths

TOKEN_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)


def percentile(values: list[float], percentile_value: int) -> float:
    if len(values) == 1:
        return values[0]
    quantiles = statistics.quantiles(values, n=100, method="inclusive")
    return quantiles[percentile_value - 1]


def write_synthetic_vault(vault: Path, pages: int) -> None:
    concepts = vault / "concepts"
    concepts.mkdir(parents=True)
    for number in range(pages):
        codename = f"artifact{number:05d}"
        topic = f"habitat{number % 37:02d}"
        content = f"""---
type: Concept
title: Synthetic field record {number:05d}
description: Fictional observation for {codename} in {topic}.
tags: [synthetic, fieldwork, {topic}]
sources:
  - resource: synthetic://record/{number:05d}
generated:
  by: process:benchmark
  at: 2026-09-01T00:00:00Z
status: stable
---

# Synthetic field record {number:05d}

The fictional Aurora team stored calibration notes for {codename}. This record concerns
offline estuary fieldwork in {topic}, seasonal monitoring, and a portable sensor dossier.
"""
        (concepts / f"record-{number:05d}.md").write_text(
            content, encoding="utf-8", newline="\n"
        )


def cases(pages: int, query_count: int) -> list[tuple[str, str]]:
    if query_count > pages:
        raise ValueError("queries cannot exceed pages")
    step = max(1, pages // query_count)
    numbers = list(range(0, pages, step))[:query_count]
    return [
        (
            f"find the portable sensor dossier for artifact{number:05d}",
            f"concepts/record-{number:05d}.md",
        )
        for number in numbers
    ]


def full_markdown_scan(vault: Path, text: str, limit: int) -> list[str]:
    tokens = [token.casefold() for token in TOKEN_RE.findall(text)]
    ranked: list[tuple[int, str]] = []
    for path in iter_page_paths(vault):
        relative = path.relative_to(vault).as_posix()
        content = path.read_text(encoding="utf-8-sig").casefold()
        score = sum(content.count(token) for token in tokens)
        if score:
            ranked.append((score, relative))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [path for _, path in ranked[:limit]]


def measure(
    name: str,
    search,
    benchmark_cases: list[tuple[str, str]],
    runs: int,
    top_k: int,
) -> dict[str, object]:
    latencies: list[float] = []
    hits = 0
    total = runs * len(benchmark_cases)
    for _ in range(runs):
        for text, expected in benchmark_cases:
            started = time.perf_counter()
            paths = search(text, top_k)
            latencies.append((time.perf_counter() - started) * 1000)
            hits += int(expected in paths)
    return {
        "method": name,
        "queries": total,
        "top_k": top_k,
        "hits": hits,
        "recall": hits / total,
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(percentile(latencies, 95), 3),
        "mean_ms": round(statistics.mean(latencies), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=500)
    parser.add_argument("--queries", type=int, default=20)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="esb-comparison-") as raw:
        vault = Path(raw)
        write_synthetic_vault(vault, args.pages)
        settings = Settings(vault=vault, config_file=None, max_results=args.top_k)
        benchmark_cases = cases(args.pages, args.queries)
        rebuild_started = time.perf_counter()
        rebuild(settings)
        rebuild_ms = (time.perf_counter() - rebuild_started) * 1000

        # Warm both paths once so startup and filesystem cache effects are not assigned
        # to only one method. Each timed FTS5 query still includes incremental sync.
        query(settings, benchmark_cases[0][0], limit=args.top_k, track=False)
        full_markdown_scan(vault, benchmark_cases[0][0], args.top_k)

        fts5 = measure(
            "SQLite FTS5 (incremental sync + BM25)",
            lambda text, limit: [
                item.path
                for item in query(settings, text, limit=limit, track=False)
            ],
            benchmark_cases,
            args.runs,
            args.top_k,
        )
        markdown = measure(
            "Full Markdown scan (read every file)",
            lambda text, limit: full_markdown_scan(vault, text, limit),
            benchmark_cases,
            args.runs,
            args.top_k,
        )
        speedup = float(markdown["p50_ms"]) / float(fts5["p50_ms"])
        time_saved = 1 - float(fts5["p50_ms"]) / float(markdown["p50_ms"])
        report = {
            "date": datetime.now(UTC).date().isoformat(),
            "os": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "synthetic_pages": args.pages,
            "distinct_cases": len(benchmark_cases),
            "runs": args.runs,
            "index_rebuild_ms": round(rebuild_ms, 3),
            "methods": [fts5, markdown],
            "p50_speedup": round(speedup, 3),
            "p50_time_saved_percent": round(time_saved * 100, 1),
            "scope": "Local retrieval only; excludes model generation and network latency.",
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
