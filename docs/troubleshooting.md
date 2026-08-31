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

## The easy installer cannot download the app

Check the internet connection and rerun the installer. It downloads one standalone application
from this repository's GitHub release. Corporate networks may need to allow GitHub release
downloads. It does not install Python or modify the shell configuration.

## “No vault configured”

Pass `--vault`, set `ESB_VAULT_PATH`, or create `second-brain.toml`. The toolkit intentionally refuses to guess.

## FTS5 is unavailable

Rerun the installer and use the internal `doctor` operation from the [engine reference](engine-reference.md). FTS5 is bundled in the standalone application.

## Search misses a paraphrase

FTS5 is lexical. Add useful vocabulary to the page description or tags and measure the result with a private benchmark. The project deliberately does not add embeddings or another retrieval engine based on an anecdote.

## The index looks stale

Run `esb index update --verify-hashes`, then `esb index rebuild` if needed. The database is disposable.

## A page will not archive

Run `esb prune candidates` and inspect age, usage, score, and backlinks. Hard protections intentionally override coldness.

## Backup failed

Read the exact Git error, confirm a private remote exists, set `[backup] enabled = true` only after verifying privacy, and check the current branch name. A failure is safer than reporting an unverified backup.
