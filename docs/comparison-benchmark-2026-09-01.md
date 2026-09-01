# Controlled retrieval comparison — 2026-09-01

This benchmark compares two local retrieval paths over exactly the same controlled test corpus and
questions. The notes were generated for the benchmark and contain no private vault content.

## Environment and dataset

| Item | Value |
|---|---|
| Date | 2026-09-01 |
| OS | Windows 11, build 26200 |
| CPU | Intel Core i7-13620H |
| Architecture | AMD64 |
| Python | 3.12.10 |
| Test pages | 500 |
| Distinct questions | 20 |
| Timed runs | 3 |
| Total measured queries per method | 60 |
| Top-k | 5 |

Every generated page is an OKF Markdown file about a benchmark field record. Every question has one
known expected page. The test warms both paths once before timing them.

## Result

| Method | Top-five hits | Recall | Median | p95 | Mean |
|---|---:|---:|---:|---:|---:|
| SQLite FTS5, including incremental freshness scan and BM25 | 60/60 | 100% | 180.274 ms | 225.910 ms | 183.151 ms |
| Full Markdown scan, reading and scoring all 500 files | 60/60 | 100% | 224.931 ms | 285.641 ms | 227.968 ms |

The useful note appeared **44.657 ms sooner**, which is **19.9% less local searching time** on this
test. The initial FTS5 index build took **3,894.788 ms**; that one-time cost is not hidden inside the
warm-query comparison.

FTS5 checks which notes changed without reopening the content of every unchanged note. It then shows
the agent at most five notes that are likely to contain the answer. The other method reopens and
checks all 500 notes for every question. In practical terms, the agent receives a short, useful
reading list instead of searching the entire folder again.

## What this does and does not prove

- It proves the numbers above for this machine, dataset, implementation, and run.
- It does not measure model generation, network calls, answer quality, or total conversational time.
- “No second brain” has no meaningful latency comparison for private context: a model without access
  to these test files cannot retrieve their expected pages.
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

The script creates the test vault in a temporary directory, rebuilds FTS5, warms both methods,
prints a machine-readable JSON report, and removes the temporary corpus afterward.
