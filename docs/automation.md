# Agent-driven automation

The default installation creates no Task Scheduler, launchd, cron, or systemd entry. Instead, the
managed agent instructions run one provider-neutral `context "<request>"` command at the start of
each request. It advances the interaction counter under a file lock, updates changed Markdown in
FTS5, searches for relevant context, and records returned pages as weak usage. There is no separate
maintenance command for an agent to remember during ordinary work.

The default cadence is:

- Every request: one `context` call; cheap state check plus incremental indexing and local search.
- After 24 hours or 50 requests, whichever comes first: strict OKF reconciliation, FTS5 verification,
  and utility recalculation.
- After 30 days: return cold candidates to the agent. The agent reads them and records its selection
  with `maintenance review`; the engine never archives the entire list blindly by default.
- After 24 hours, when private backup is explicitly enabled: run the validated private Git backup.

The interaction threshold handles periods of intense editing. The time threshold catches up after a
quiet period. If no agent request occurs, nothing runs; the next request performs the overdue work.
That is safe because an inactive agent is not creating new knowledge. This protocol is independent
of the model provider, but the host application must be able to run local commands and retain the
managed instruction. A browser-only chat cannot operate this local loop by itself.

The maintenance state and usage ledger travel in the portable bundle. Derived scores and FTS5 do not;
they are rebuilt after restoration.

## Optional unattended scheduling

Use `<application> --vault <vault> install --with-os-automation` only when maintenance must run even
with no agent interaction. Daily verified backup is included only when a Git remote exists **and**
`[backup] enabled = true` explicitly confirms that the destination is private. Repository visibility
cannot be inferred from a URL.

The commands below are implementation details for repairing or customizing that optional schedule.
Replace `enhanced-second-brain` with the absolute path to the standalone application.

### Windows Task Scheduler

Import and customize [`automation/windows/enhanced-second-brain.xml`](../automation/windows/enhanced-second-brain.xml), or create a task that runs:

```powershell
enhanced-second-brain --vault C:\Knowledge\second-brain reconcile
```

### macOS launchd

Copy [`automation/macos/com.example.enhanced-second-brain.plist`](../automation/macos/com.example.enhanced-second-brain.plist) to `~/Library/LaunchAgents/`, replace the executable and vault placeholders, then run:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.enhanced-second-brain.plist
```

### Linux systemd-user

Copy the files in [`automation/linux`](../automation/linux/) to `~/.config/systemd/user/`, replace placeholders, then run:

```bash
systemctl --user daemon-reload
systemctl --user enable --now enhanced-second-brain.timer
```

Every scheduler should treat non-zero exits as failures. Unattended archival uses deterministic hard
guards but cannot perform the agent's semantic review, so agent-driven mode remains the recommended
default. Archive and backup commands intentionally fail closed when validation or safety checks fail.
