# Capture hook measurements — October 12, 2026

Measured on Windows 11 (build 26300), Python 3.12.10, with the v0.8.0 portable directory
application built using PyInstaller 6.22.2. Each scenario has 30 samples after a warm-up.
The corpus is synthetic and all benchmark vaults are temporary.

| Initial corpus | Scenario | Median | P95 |
|---|---|---:|---:|
| 500 pages | Idle Stop, engine already imported | 1.510 ms | 2.451 ms |
| 2,500 pages | Idle Stop, engine already imported | 1.370 ms | 2.213 ms |
| 500 pages | One-page capture with validation, atomic writes and indexing | 45.491 ms | 55.873 ms |
| 2,500 pages | One-page capture with validation, atomic writes and indexing | 43.974 ms | 55.910 ms |
| 500 pages | Idle Stop, complete portable process invocation | 167.947 ms | 209.602 ms |
| 2,500 pages | Idle Stop, complete portable process invocation | 190.707 ms | 209.835 ms |

Both idle targets pass here: engine P95 below 20 ms and portable process P95 below 500 ms.
Capture includes creating the turn receipt, validating a new page, the recovery journal,
atomic publication, touched-path FTS indexing and checkpoint completion. Each sample adds
one synthetic page, so the final corpus is 30 pages larger than its initial size.

The idle path reads session/checkpoint files and does not walk the corpus. A one-page capture
touches only that page, which explains the similar timings at both corpus sizes. This does
not remove the conservative freshness scan used by prompt-start retrieval. No speedup of
complete model answers is claimed: semantic work, tool transport, native shell startup,
network backup and model generation are outside these engine measurements. The portable
process scenario includes the runtime startup but not the native provider's shell wrapper.

Reproduce from the developer environment:

```text
python scripts/benchmark_hooks.py --pages 500 2500 --repeats 30 --executable <portable-application>
```

The script deletes its temporary vaults. The release build also executes a portable smoke
test covering generic events, durable capture, empty receipts and actual Codex/Claude
command invocation shapes using isolated provider configurations. Native provider trust
and a real agent session still require verification in the host application.
