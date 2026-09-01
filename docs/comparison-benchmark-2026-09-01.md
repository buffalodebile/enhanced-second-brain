# Synthetic retrieval comparison — 2026-09-01

This benchmark compares two local retrieval paths over exactly the same fictional corpus and
questions. It contains no private vault content.

## Environment and dataset

| Item | Value |
|---|---|
| Date | 2026-09-01 |
| OS | Windows 11, build 26200 |
| CPU | Intel Core i7-13620H |
| Architecture | AMD64 |
| Python | 3.12.10 |
| Synthetic pages | 500 |
| Distinct questions | 20 |
| Timed runs | 3 |
| Total measured queries per method | 60 |
| Top-k | 5 |

Every generated page is an OKF Markdown file about a fictional field record. Every question has one
known expected page. The test warms both paths once before timing them.

## Result

| Method | Top-five hits | Recall | Median | p95 | Mean |
|---|---:|---:|---:|---:|---:|
| SQLite FTS5, including incremental freshness scan and BM25 | 60/60 | 100% | 180.274 ms | 225.910 ms | 183.151 ms |
| Full Markdown scan, reading and scoring all 500 files | 60/60 | 100% | 224.931 ms | 285.641 ms | 227.968 ms |

The FTS5 path used **19.9% less median local retrieval time**. Expressed as throughput, the full-scan
median divided by the FTS5 median is **1.248×**. The initial FTS5 index build took **3,894.788 ms**;
that one-time cost is not hidden inside the warm-query comparison.

FTS5 checks the metadata of all eligible pages for freshness, but it does not reopen unchanged
Markdown bodies. It then returns at most five ranked candidates. The full-scan baseline reopens and
scores all 500 bodies for every question. Five candidates versus 500 bodies is a 99% smaller set at
the handoff to the agent, although the agent may choose to open fewer than five.

## What this does and does not prove

- It proves the numbers above for this machine, dataset, implementation, and run.
- It does not measure model generation, network calls, answer quality, or total conversational time.
- “No second brain” has no meaningful latency comparison for private context: a model without access
  to these fictional files cannot retrieve their expected pages.
- A native exact-text search can be faster for a known literal or filename. This baseline instead
  represents the common fallback of reopening and ranking every Markdown file for a natural-language
  question.
- Corpus size, page length, filesystem cache, antivirus, hardware, and query vocabulary can change
  both latency and recall. Users should benchmark their own vault.

## Reproduce

From a source checkout with the development environment installed:

```bash
python scripts/benchmark_comparison.py --pages 500 --queries 20 --runs 3 --top-k 5
```

The script creates the synthetic vault in a temporary directory, rebuilds FTS5, warms both methods,
prints a machine-readable JSON report, and removes the temporary corpus afterward.
