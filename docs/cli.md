# Command-line reference

Most people only need the easy installer shown in the README. This page is for manual operation,
debugging, and agent integrations.

Every command accepts a vault through `--vault`, `ESB_VAULT_PATH`, or the nearest
`second-brain.toml` file.

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

`python -m enhanced_second_brain` and `esb` are equivalent. The module form is useful when the
Python scripts directory is not on `PATH`.

## Common operations

```bash
# Check the installation
python -m enhanced_second_brain --vault ~/second-brain doctor

# Search notes
python -m enhanced_second_brain --vault ~/second-brain index query "what did we decide?"

# Read one result and record that it supported an answer
python -m enhanced_second_brain --vault ~/second-brain page read projects/example.md
python -m enhanced_second_brain --vault ~/second-brain usage record cited projects/example.md

# Reconcile notes and refresh the local index
python -m enhanced_second_brain --vault ~/second-brain reconcile

# Preview pages eligible for reversible archival
python -m enhanced_second_brain --vault ~/second-brain prune candidates
```

Run any command with `--help` to see its arguments. Read [agent and MCP integration](agent-and-mcp.md)
for the optional local tool bridge and [backup/restore](backup-restore.md) before enabling remote
backup.
