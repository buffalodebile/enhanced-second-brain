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
- **Adaptive link graph:** used only for paths, dependencies, impact, and multi-step questions.
- **Local usage ledger:** records page injection, opening, and citation without storing prompts or
  answers. See [usage and archival](usage-and-archival.md).
- **Native scheduling:** daily reconciliation and monthly reversible archival on Windows, macOS,
  and Linux. See [automation](automation.md).
- **Optional MCP stdio bridge:** available for clients that want native tools, but not installed by
  default. The ordinary Codex workflow uses generated instructions and the local command directly.
  See [agent and MCP integration](agent-and-mcp.md).
- **Private bootstrap runtime:** the easy installers use Astral `uv` to create an isolated Python
  environment inside the application data directory. Users do not need Python, Git, `uv`, or a
  modified `PATH`; the bootstrap does not run as a daemon.

FTS5 is the default because it fits the project's lightweight, zero-daemon constraints. It is not
universally superior to semantic retrieval; paraphrases with no shared vocabulary can be missed.
The included benchmark lets each user test that trade-off on their own corpus.

## Safety and portability

Archival moves eligible pages to a dated folder and never deletes them automatically. Remote backup
is disabled until a private Git destination is explicitly enabled. Read the [threat model](threat-model.md)
and [backup/restore guide](backup-restore.md) before connecting a real vault.

Developers and agents can use the full [CLI reference](cli.md). The `esb` command and
`python -m enhanced_second_brain` expose the same interface.
