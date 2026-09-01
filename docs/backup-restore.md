# Backup and restore

This page covers continuous private Git backup, including version history and dirty snapshots. For
a single standard ZIP that can move the knowledge context between machines, editors, or local AI
agents, use the [portable export guide](context-sovereignty.md). The two mechanisms complement each
other: Git is the recovery history; the portable bundle is the clean transfer format.

Use a **private** Git repository for a real vault.

Agent-driven backup is deliberately off until the vault's `second-brain.toml` contains:

```toml
[backup]
enabled = true
remote = "origin"
```

Set this only after verifying the remote is private and access-controlled. The first agent request
after 24 hours then runs the backup; unattended OS scheduling remains an explicit option. Manual
backup remains an advanced operation in the [engine reference](engine-reference.md).

The backup operation first runs a strict Enhanced OKF audit. It pushes the existing local `main`
commit and verifies the remote SHA. It never creates a main-branch commit from dirty files.

For a dirty worktree, it creates an isolated snapshot commit through a temporary `GIT_INDEX_FILE`:

1. seed the temporary index from `HEAD`;
2. stage the worktree without touching the real index;
3. force-add the ignored private usage ledger and portable maintenance state;
4. write the tree twice and require an identical object ID;
5. require that `HEAD` did not move;
6. create a commit with `git commit-tree`;
7. push to `backup-snapshot` with `--force-with-lease`;
8. verify the remote SHA.

Secret-like untracked filenames stop the snapshot. This is a guardrail, not a replacement for secret scanning.

## Restore

Clone the private repository, select `main` for validated knowledge or `backup-snapshot` for the last dirty snapshot, install the toolkit, and run:

```bash
enhanced-second-brain --vault /restored/vault okf audit
enhanced-second-brain --vault /restored/vault index rebuild
enhanced-second-brain --vault /restored/vault doctor
```

The FTS cache is deliberately absent and reconstructs from Markdown. Test a clean clone regularly; a successful push does not prove that every path is restorable on another operating system.
