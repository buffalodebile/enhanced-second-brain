# Technical overview

This page contains the implementation details intentionally omitted from the main README.

## Design goals

Enhanced Second Brain is optimized for a local, daily-use knowledge base that remains portable and
cheap to maintain. Markdown files are authoritative; every database or report can be rebuilt from
them.

## Stack

- **Enhanced OKF v0.2 profile:** consistent metadata and portable knowledge pages. The project keeps
  its governance extensions separate from the official OKF fields. See [OKF profile](okf-profile.md).
- **SQLite FTS5/BM25:** incremental Unicode-aware retrieval without embeddings, a GPU, or a search
  daemon. See [retrieval and benchmarks](retrieval-and-benchmarks.md).
- **Local usage ledger:** records page injection, opening, and citation without storing prompts or
  answers. See [usage and archival](usage-and-archival.md).
- **Native scheduling:** daily reconciliation and monthly reversible archival on Windows, macOS,
  and Linux. See [automation](automation.md).
- **One standalone application:** CI bundles the engine separately for Windows, Linux, Intel Mac,
  and Apple Silicon Mac. The installing agent downloads that single versioned file and verifies its
  checksum. No separate runtime, package manager, plugin, or background database service is needed.

FTS5 is the default because it fits the project's lightweight, zero-daemon constraints. It is not
universally superior to semantic retrieval; paraphrases with no shared vocabulary can be missed.
The included benchmark lets each user test that trade-off on their own corpus.

## Why SQLite rather than libSQL

[libSQL](https://github.com/tursodatabase/libsql) is a SQLite-compatible fork maintained by Turso.
Its differentiating features are embedded replicas and remote database access. It preserves the
SQLite file format and API compatibility, but also inherits SQLite's single-writer model; the project
now directs new feature development toward the separate Turso database engine.

Those features solve a different problem. Enhanced Second Brain keeps its authoritative data in
portable OKF Markdown and treats the FTS5 database as a local cache that can be rebuilt. Replicating
that cache would add a native driver, synchronization state, remote configuration, and a larger
cross-platform test surface without improving FTS5's lexical ranking. The current Python libSQL API
is also marked experimental by its maintainers.

SQLite therefore remains the smaller and more mature default. libSQL would become relevant only if
the product later needed a remotely hosted database or low-latency embedded replicas across several
machines. Even then, the portable OKF files—not the search cache—would remain the source of truth.

## Safety and portability

Archival moves eligible pages to a dated folder and never deletes them automatically. Remote backup
is disabled until a private Git destination is explicitly enabled. Read the [threat model](threat-model.md)
and [backup/restore guide](backup-restore.md) before connecting a real vault.

The application has an internal command interface so local AI agents and the operating-system
scheduler can operate it. End users do not need to learn it. Maintainers can read the
[engine reference](engine-reference.md).
