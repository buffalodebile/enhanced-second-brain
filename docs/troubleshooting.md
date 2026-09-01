# Troubleshooting

## Use an existing notes folder

Give the absolute folder path to the installing agent together with the repository URL. The agent
must pass that exact path to the application rather than creating `~/SecondBrain`. A dated safety
copy of every Markdown file requiring migration is created before it is changed.

## The agent cannot download the application

Check the internet connection and GitHub release access. Corporate networks may need to allow
release downloads. The agent must download both the matching standalone application and
`SHA256SUMS`, then verify integrity before execution.

## “No vault configured”

Pass `--vault`, set `ESB_VAULT_PATH`, or create `second-brain.toml`. The toolkit intentionally refuses to guess.

## FTS5 is unavailable

Ask the agent to run the internal `doctor` operation from the [engine reference](engine-reference.md).
FTS5 is bundled in the standalone application.

## Search misses a paraphrase

FTS5 is lexical. Add useful vocabulary to the page description or tags and measure the result with a private benchmark. The project deliberately does not add embeddings or another retrieval engine based on an anecdote.

## The index looks stale

Run `esb index update --verify-hashes`, then `esb index rebuild` if needed. The database is disposable.

## A page will not archive

Run `esb prune candidates` and inspect age, usage, score, and backlinks. Hard protections intentionally override coldness.

## Backup failed

Read the exact Git error, confirm a private remote exists, set `[backup] enabled = true` only after verifying privacy, and check the current branch name. A failure is safer than reporting an unverified backup.
