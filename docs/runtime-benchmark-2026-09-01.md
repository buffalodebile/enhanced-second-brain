# Runtime overhead benchmark — 2026-09-01

This benchmark isolates the `context` command used at the start of a local agent request. It measures
process startup, immediate file freshness, FTS5 ranking, prompt-cadence state, and one locked batch of
usage telemetry. It does not measure model inference, network latency, or final answer quality.

## Environment

- Windows 11
- Intel Core i7-13620H
- Python 3.12.10
- PyInstaller 6.22.2
- 238 generated Markdown notes
- 15 warmed repetitions per configuration
- Two returned context pages

## Results

| Configuration | Before | After | Change |
|---|---:|---:|---:|
| Private provider-neutral wrapper, external process | 217.930 ms | 154.973 ms | 28.9% less time |
| Public source CLI, external process | 532.261 ms | 324.373 ms | 39.1% less time |
| Public engine in one warm process | 89.832 ms | 80.107 ms | 10.8% less time |

The code changes remove a nested Python process in the private wrapper, reuse one SQLite connection
for refresh and search, write all injected usage events under one lock, and prune excluded directories
before walking them. Immediate visibility of new, changed, renamed, and deleted Markdown remains the
default. No daemon, model, GPU process, watcher, or new dependency was introduced.

## Why the release is a ZIP directory bundle

With the optimized code held constant, the Windows PyInstaller formats measured:

| Release shape | Median complete `context` call |
|---|---:|
| Compressed one-file executable | 1,551.057 ms |
| Self-contained directory bundle | 275.202 ms |

The one-file build had to unpack its embedded runtime on every agent request. The directory bundle
was 82.3% faster in this controlled run. It contains 27 files totaling about 22.0 MB before ZIP
compression, including the private runtime libraries, but no Python installation or package manager.
The installing agent verifies one release ZIP, extracts the directory once, and records the executable's
stable path. The human still installs no runtime, plugin, database server, scheduler, or background service.

These are same-machine engineering measurements, not universal speed promises. Antivirus behavior,
filesystem caching, note count, storage, operating system, and executable signing can change startup
latency. The important invariant is reproducible: the release avoids repeated one-file extraction while
keeping the entire application local and relocatable.
