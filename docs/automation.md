# Cross-platform automation

The easy installer creates the native user-level schedule automatically. End users do not need to
configure or run it. Daily verified backup is included only when a Git remote exists **and**
`[backup] enabled = true` explicitly confirms that the destination is private. The installer cannot
infer repository visibility from a URL.

The installed schedule uses this cadence:

- Daily: `reconcile`; optionally `backup` to a private Git remote.
- Weekly: `index update --verify-hashes` and `score`.
- Monthly: `prune apply --all-candidates`. The first run waits for its calendar time rather than running during installation. Eligibility is conservative and archival remains reversible; inspect `prune candidates` at any time.

## Manual recovery for operators

The commands below are implementation details for repairing a schedule. Replace
`enhanced-second-brain` with the absolute path to the installed standalone application.

### Windows Task Scheduler

Import and customize [`automation/windows/enhanced-second-brain.xml`](../automation/windows/enhanced-second-brain.xml), or create a task that runs:

```powershell
enhanced-second-brain --vault C:\Knowledge\second-brain reconcile
```

The automatic installer enables “Start when available” and allows runs on battery, so a missed laptop run is recovered after the user session returns. If the task must run while fully logged out, configure credentials through Task Scheduler rather than putting passwords in scripts.

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

Every scheduler should treat non-zero exits as failures. Archive and backup commands intentionally fail closed when validation or safety checks fail.
