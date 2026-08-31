# Troubleshooting

## Use an existing notes folder

The easy installer creates `SecondBrain` in your home folder by default. To adopt another folder,
set `ESB_VAULT_PATH` before running it.

Windows PowerShell:

```powershell
$env:ESB_VAULT_PATH = "C:\path\to\your\notes"
.\install.cmd
```

macOS or Linux:

```bash
curl -fsSL https://github.com/buffalodebile/enhanced-second-brain/releases/latest/download/install.sh | ESB_VAULT_PATH="$HOME/path/to/notes" sh
```

The installer creates a dated safety copy of Markdown files that need migration.

## The easy installer cannot download its runtime

Check the internet connection and rerun the installer. It downloads a private `uv` bootstrap from
Astral and uses it to install an isolated Python runtime. It does not change the system Python or
shell configuration. Corporate networks may need to allow `astral.sh`, GitHub release downloads,
and the Python standalone distribution host.

## “No vault configured”

Pass `--vault`, set `ESB_VAULT_PATH`, or create `second-brain.toml`. The toolkit intentionally refuses to guess.

## FTS5 is unavailable

Run `esb doctor`. Standard CPython builds normally include FTS5; custom Python distributions may omit it. Install a Python build whose SQLite reports `ENABLE_FTS5`.

## Search misses a paraphrase

FTS5 is lexical. Add useful vocabulary to the page description/tags, use graph retrieval if the relationship is structural, or evaluate a semantic layer against a private benchmark. Do not add embeddings based on an anecdote.

## The index looks stale

Run `esb index update --verify-hashes`, then `esb index rebuild` if needed. The database is disposable.

## A page will not archive

Run `esb prune candidates` and inspect age, usage, score, and backlinks. Hard protections intentionally override coldness.

## MCP write refused

Set `mcp.allow_writes=true` only if the connecting agent is trusted to modify local state. Restart the stdio process after changing configuration.

## Codex does not show the MCP tools

Project MCP configuration is loaded only after the vault is trusted. Open Codex in the vault, accept the trust prompt, restart the client, and use `/mcp` to inspect the connection. The global `AGENTS.md` integration and direct CLI workflow do not depend on MCP.

## Backup failed

Read the exact Git error, confirm a private remote exists, set `[backup] enabled = true` only after verifying privacy, and check the current branch name. A failure is safer than reporting an unverified backup.
