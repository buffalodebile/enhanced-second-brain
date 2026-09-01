# Agent installation protocol

This protocol is for any local AI agent that can access the filesystem, run commands, and edit its
own persistent instructions. The human should only need to provide this repository URL and the
location of an existing notes folder, if they have one.

## Goal

Install one standalone Enhanced Second Brain application, initialize or adopt the vault, enable
automatic maintenance, connect the current agent, and verify the result. Do not ask the human to
install Python, a package manager, a plugin, or a database server.

## Procedure

1. Choose the vault path. Preserve a path explicitly supplied by the human; otherwise use
   `~/SecondBrain`.
2. Detect the operating system and CPU architecture, then select the matching release asset:

   | System | Asset |
   |---|---|
   | Windows x64 | `enhanced-second-brain-windows-x64.exe` |
   | Linux x64 | `enhanced-second-brain-linux-x64` |
   | macOS Apple Silicon | `enhanced-second-brain-macos-arm64` |
   | macOS Intel | `enhanced-second-brain-macos-x64` |

3. Download the asset and `SHA256SUMS` from the latest GitHub release. Verify the asset hash before
   executing it. Stop and report an integrity failure if the checksum does not match.
4. Store the application in a stable user-owned directory:
   - Windows: `%LOCALAPPDATA%\EnhancedSecondBrain\enhanced-second-brain.exe`
   - macOS/Linux: `${XDG_DATA_HOME:-~/.local/share}/enhanced-second-brain/enhanced-second-brain`
5. On macOS/Linux, make the application executable. On macOS, if Gatekeeper quarantined the
   downloaded file, explain the signed-code limitation before asking for any security override.
6. Run:

   ```text
   <application> --vault <vault> install
   <application> --vault <vault> doctor
   ```

7. Read the managed block written to `<vault>/AGENTS.md`. Connect that block to the current agent's
   native persistent-instruction mechanism so context lookup also works outside the vault. Preserve
   all existing user instructions and do not create a provider-specific dependency inside the vault.
8. Verify that `doctor` reports `fts5: true`, a valid strict OKF audit, and an existing index. Verify
   that daily reconciliation and monthly reversible archival were scheduled by the operating system.
9. Report the vault path, application path, verification result, and any limitation. Do not claim
   that browser-only chat interfaces can access local files.

Re-running the same procedure upgrades the application and reconciles the vault idempotently. A
dated safety copy is created before any existing Markdown file is migrated.
