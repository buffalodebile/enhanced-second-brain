---
name: enhanced-second-brain
description: Install, operate, diagnose, or improve a local-first Enhanced Second Brain vault using OKF-compatible Markdown, SQLite FTS5, adaptive graph retrieval, weighted usage, reversible archival, backups, and optional MCP. Use for second-brain setup, vault search, lifecycle maintenance, portability, agent integration, or troubleshooting; not for pure web chats with no filesystem, command, or MCP access.
---

# Enhanced Second Brain

Use the `esb` CLI as the stable interface. Treat Markdown as authoritative and the FTS database as a disposable local cache.

## Workflow

1. For first-time setup or adoption, run `esb --vault <path> install`; it installs the normal automated workflow without requiring this skill at runtime.
2. Resolve configuration without guessing: `--vault`, then `ESB_VAULT_PATH`, then nearest `second-brain.toml`.
3. Run `esb doctor` and `esb okf audit` before changes.
4. For ordinary questions, run `esb index query` and read only useful pages.
5. Use `esb graph` only for paths, impact, hubs, clusters, or bridges.
6. Record `cited` only when a page materially supports the answer.
7. Use `esb page upsert` for knowledge changes, then `esb reconcile`.
8. Inspect `esb prune candidates` whenever useful; scheduled archival remains reversible. Never delete knowledge automatically.
9. Keep real vaults and usage ledgers private.

Read [references/operations.md](references/operations.md) for command patterns and safety boundaries. Refer users to the repository documentation for installation, automation, and recovery.
