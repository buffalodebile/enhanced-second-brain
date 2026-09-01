# FTS5 retrieval and benchmarks

## Incremental FTS5

The cache lives at `_meta/cache/esb-fts.sqlite3` and is excluded from Git. Each update compares file size and modification time; new and modified pages are inserted, deleted or archived pages are removed, and renames become remove-plus-add. A periodic `--verify-hashes` pass checks SHA-256 content hashes.

FTS5 uses the `unicode61` tokenizer with diacritic removal. BM25 weights title, tags, description, headings, and body differently. Query tokens are OR-combined to work well with natural-language lookups while still rewarding pages matching multiple terms.

## Reproducible benchmark

`benchmark.json` is a list of fictional queries and expected page paths. The internal benchmark rebuilds the cache, executes each case, reports top-k recall, p50/p95 latency, OS, machine architecture, engine version, and date, then exits non-zero unless recall is 100% or an optional latency threshold is met.

Do not copy a benchmark number to another vault as a promise. Corpus size, query vocabulary, disk cache, antivirus, Python build, and hardware all affect results. Use the demo only to verify installation; use a private, labeled dataset to decide whether lexical retrieval is sufficient for your own content.

The first published fictional result is [recorded with its environment and date](demo-benchmark-2026-08-31.md).
The larger [comparative benchmark](comparison-benchmark-2026-09-01.md) measures FTS5 against a full
Markdown-file scan. It reports retrieval time only and intentionally makes no end-to-end AI latency
or intelligence claim.
