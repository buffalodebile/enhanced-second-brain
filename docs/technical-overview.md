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
  and Apple Silicon Mac. The installer downloads that single versioned file. It does not install a
  Python runtime, package manager, plugin, skill, agent, MCP server, or background database service.

FTS5 is the default because it fits the project's lightweight, zero-daemon constraints. It is not
universally superior to semantic retrieval; paraphrases with no shared vocabulary can be missed.
The included benchmark lets each user test that trade-off on their own corpus.

## Safety and portability

Archival moves eligible pages to a dated folder and never deletes them automatically. Remote backup
is disabled until a private Git destination is explicitly enabled. Read the [threat model](threat-model.md)
and [backup/restore guide](backup-restore.md) before connecting a real vault.

The application has an internal command interface so Codex and the operating-system scheduler can
operate it. End users do not need to learn it. Maintainers can read the [engine reference](engine-reference.md).
