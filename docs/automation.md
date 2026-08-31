# Cross-platform automation

`esb --vault /path/to/brain install` installs the native user-level schedule automatically. Daily verified backup is included only when a Git remote exists **and** `[backup] enabled = true` explicitly confirms that the destination is private. The installer cannot infer repository visibility from a URL. Rerun `install` after opting in. The files below remain inspectable templates for operators who prefer manual deployment. Run commands from an installed `esb` executable and use an absolute vault path. Store logs outside the vault or in an ignored operational directory.

Recommended cadence:

- Daily: `reconcile`; optionally `backup` to a private Git remote.
- Weekly: `index update --verify-hashes` and `score`.
- Monthly: `prune apply --all-candidates`. The first run waits for its calendar time rather than running during installation. Eligibility is conservative and archival remains reversible; inspect `prune candidates` at any time.

## Windows Task Scheduler

Import and customize [`automation/windows/enhanced-second-brain.xml`](../automation/windows/enhanced-second-brain.xml), or create a task that runs:

```powershell
esb --vault C:\Knowledge\second-brain reconcile
```

The automatic installer enables “Start when available” and allows runs on battery, so a missed laptop run is recovered after the user session returns. If the task must run while fully logged out, configure credentials through Task Scheduler rather than putting passwords in scripts.

## macOS launchd

Copy [`automation/macos/com.example.enhanced-second-brain.plist`](../automation/macos/com.example.enhanced-second-brain.plist) to `~/Library/LaunchAgents/`, replace the executable and vault placeholders, then run:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.enhanced-second-brain.plist
```

## Linux systemd-user

Copy the files in [`automation/linux`](../automation/linux/) to `~/.config/systemd/user/`, replace placeholders, then run:

```bash
systemctl --user daemon-reload
systemctl --user enable --now enhanced-second-brain.timer
```

Every scheduler should treat non-zero exits as failures. Archive and backup commands intentionally fail closed when validation or safety checks fail.
