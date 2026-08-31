# Synthetic demo benchmark — 2026-08-31

This result uses only the fictional four-page vault in `examples/demo-vault`. It is an installation check, not a universal performance claim.

| Environment | Value |
|---|---|
| Date | 2026-08-31 |
| OS | Windows 11, build 26200 |
| Machine architecture | AMD64 |
| Python | 3.12.10 |
| Queries | 5 |
| Top-k | 5 |
| Top-five retrieval | 5/5 (100%) |
| Median | 2.574 ms |
| p95 | 12.680 ms |

The cache was rebuilt immediately before the queries. The benchmark includes the incremental synchronization performed by each query. Hardware model is intentionally omitted because the tiny synthetic corpus does not justify hardware-level comparisons.

Reproduce it with:

```bash
enhanced-second-brain --vault examples/demo-vault benchmark examples/demo-vault/benchmark.json --max-p95-ms 1000
```

Hosted CI uses a 2000 ms threshold to tolerate runner variability while still requiring 100% top-five retrieval.
