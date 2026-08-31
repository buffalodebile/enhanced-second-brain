# Enhanced Second Brain

[![CI](https://github.com/buffalodebile/enhanced-second-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/buffalodebile/enhanced-second-brain/actions/workflows/ci.yml)

Enhanced Second Brain is a local-first toolkit for portable Markdown knowledge. It combines an **Enhanced OKF v0.2 profile**, SQLite **FTS5**, adaptive graph retrieval, weighted usage telemetry, reversible archival, conflict-free Git snapshots, a provider-neutral CLI, an Agent Skill, and an optional local MCP server.

Your Markdown files remain the source of truth. The search database is a disposable local cache. Obsidian is supported as an editor, but it is never required.

## Why this stack

- **Sovereignty:** ordinary files, standard links, Git, and a reconstructible SQLite cache.
- **Low overhead:** no embedding model, GPU process, vector daemon, or LLM API is needed.
- **Fast candidate selection:** FTS5/BM25 reads page content and metadata incrementally.
- **Structural answers:** graph traversal runs for paths, dependencies, hubs, clusters, and bridges.
- **Maintainable context:** actual use influences utility; cold content is archived, never deleted automatically.
- **Agent-neutral:** any agent with command, filesystem, or local MCP access can use the same vault.

FTS5 is the best default for this project's zero-daemon and local-first constraints. It is not universally better than embeddings: lexical search can miss paraphrases with no shared vocabulary. Benchmark your own corpus before adding a semantic layer.

## Quickstart

Requires Python 3.11+ and Git.

```bash
uv tool install "git+https://github.com/buffalodebile/enhanced-second-brain.git"
# or: pipx install "git+https://github.com/buffalodebile/enhanced-second-brain.git"

esb --vault ~/second-brain install
```

That one setup command creates or adopts the vault, preserves pre-migration Markdown, migrates and audits the Enhanced OKF profile, builds FTS5, generates utility state, installs vault instructions, adds a managed global Codex instruction block, writes a local Codex MCP entry, and schedules daily reconciliation plus monthly reversible archival. No Agent Skill invocation is required.

The global Codex block makes the vault discoverable from other repositories. It preserves existing instructions and is idempotent. The project MCP entry becomes active after the user trusts the vault in Codex, which is an intentional host security boundary. Other local agents can use the generated `CLAUDE.md`, the CLI, or the stdio MCP bridge; a toolkit cannot silently connect itself to every provider or to pure browser chats.

Then add knowledge or query immediately:

```bash
esb --vault ~/second-brain page upsert concepts/local-first.md \
  --title "Local-first systems" \
  --description "Local files remain authoritative and portable." \
  --body "# Local-first systems\n\nThe durable layer is readable without the toolkit." \
  --tag architecture
esb --vault ~/second-brain okf audit
esb --vault ~/second-brain index query "portable local files"
```

Configuration resolves in this exact order: global `--vault`, `ESB_VAULT_PATH`, then the nearest `second-brain.toml`. If none exists, the command stops with setup instructions.

To try the fictional demonstration vault:

```bash
esb --vault examples/demo-vault okf audit
esb --vault examples/demo-vault index rebuild
esb --vault examples/demo-vault index query "offline field observations"
esb --vault examples/demo-vault benchmark examples/demo-vault/benchmark.json --max-p95-ms 1000
```

## Architecture

```text
Markdown + YAML (authority)
    |-- Enhanced OKF profile -> portable knowledge
    |-- FTS5/BM25 cache      -> ordinary retrieval
    |-- link graph           -> structural/multi-hop retrieval
    |-- usage.jsonl          -> weighted local telemetry
    `-- Git                  -> validated main + isolated private snapshot
```

The profile keeps official OKF-shaped knowledge fields distinct from project governance extensions. See [the OKF profile](docs/okf-profile.md). OKF is a portability contract, not a search engine or hosting service.

## CLI

```text
esb init | install | doctor
esb okf migrate|audit
esb index update|query|status|rebuild
esb graph path|impact|hubs|clusters|bridges
esb page read|upsert
esb usage record
esb score
esb prune candidates|apply|restore
esb reconcile
esb benchmark
esb backup
esb mcp
```

Search results are recorded as `injected` (0.25), page reads as `opened` (1), and explicit citations as `cited` (2). The ledger stores no prompt text.

## MCP and agents

The local bridge is installed with the toolkit and configured project-locally for Codex:

```bash
esb --vault ~/second-brain mcp
```

MCP means Model Context Protocol. Agents launch this command on demand; people normally do not run it themselves. “stdio” means the child process communicates through its local input/output streams. It opens no network listener, runs only while the agent is connected, and has no LLM API dependency. Read tools are available by default. `record_citation` and `upsert_page` refuse writes until `mcp.allow_writes=true` in `second-brain.toml`.

The reusable skill in [`skill/enhanced-second-brain`](skill/enhanced-second-brain/SKILL.md) is optional documentation for other agent ecosystems; the installed system does not depend on it. Pure web chats without filesystem, command, or MCP access cannot reach a local vault.

## Automation and safety

- Daily: `esb reconcile`; `esb backup` is added only after explicit private-backup opt-in.
- Weekly: `esb index update --verify-hashes` and `esb score`.
- Monthly: `esb prune apply --all-candidates`; strict age, usage, link and status safeguards apply, and files are moved to a dated archive rather than deleted. Run `esb prune candidates` whenever you want to inspect the policy.

Templates are provided for [Windows Task Scheduler](docs/automation.md#windows-task-scheduler), [macOS launchd](docs/automation.md#macos-launchd), and [Linux systemd-user](docs/automation.md#linux-systemd-user).

Never publish your actual vault or telemetry ledger. The toolkit repository contains only fictional data. Read [privacy and threat model](docs/threat-model.md) and [backup/restore](docs/backup-restore.md) before enabling automation.

## Performance claims

The repository benchmark checks retrieval quality and latency on the synthetic demo vault. Results are machine-, OS-, corpus-, and date-specific. CI requires 100% top-five retrieval; latency thresholds are deliberately configurable because hosted runners vary. See [benchmark methodology](docs/retrieval-and-benchmarks.md).

## Status

`v0.1.0` is an initial public release. Back up a real vault before adopting or migrating it. The code is licensed under Apache-2.0; external specifications and dependencies retain their own licenses.
