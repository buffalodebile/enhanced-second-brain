# Agent installation protocol

This protocol is for any local AI agent that can access the filesystem, run commands, and edit its
own persistent instructions. The human should only need to provide this repository URL and the
location of an existing notes folder, if they have one.

## Goal

Install one self-contained Enhanced Second Brain application bundle, initialize or adopt the vault, enable
agent-driven automatic maintenance, connect the current agent through its normal persistent
instructions, and verify the result. Do not ask the human to install Python, a package manager, a
plugin, or a database server. Do not add a dependency on one model provider.

## Procedure

1. Choose the vault path. Preserve a path explicitly supplied by the human; otherwise use
   `~/SecondBrain`.
2. Detect the operating system and CPU architecture, then select the matching release asset:

   | System | Asset |
   |---|---|
   | Windows x64 | `enhanced-second-brain-windows-x64.zip` |
   | Linux x64 | `enhanced-second-brain-linux-x64.zip` |
   | macOS Apple Silicon | `enhanced-second-brain-macos-arm64.zip` |
   | macOS Intel | `enhanced-second-brain-macos-x64.zip` |

3. Download the ZIP asset and `SHA256SUMS` from the latest GitHub release. Verify the ZIP hash before
   extracting it. Stop and report an integrity failure if the checksum does not match.
4. Extract the ZIP into a temporary directory, then replace the stable `app` directory with the
   extracted `enhanced-second-brain/` directory. Keep its `_internal` directory beside the
   executable; never copy only the executable:
   - Windows application directory: `%LOCALAPPDATA%\EnhancedSecondBrain\app`
   - Windows executable: `%LOCALAPPDATA%\EnhancedSecondBrain\app\enhanced-second-brain.exe`
   - macOS/Linux application directory: `${XDG_DATA_HOME:-~/.local/share}/enhanced-second-brain/app`
   - macOS/Linux executable: `${XDG_DATA_HOME:-~/.local/share}/enhanced-second-brain/app/enhanced-second-brain`
   Re-running the protocol replaces the complete application directory after checksum verification.
5. On macOS/Linux, make the extracted application executable. On macOS, if Gatekeeper quarantined the
   downloaded file, explain the signed-code limitation before asking for any security override.
6. Run:

   ```text
   <application> --vault <vault> install
   <application> --vault <vault> doctor
   ```

7. Read the managed block written to `<vault>/AGENTS.md`. Connect that block to the current agent's
   native persistent-instruction mechanism so context lookup also works outside the vault. Preserve
   all existing user instructions and do not create a provider-specific dependency inside the vault.
8. Run `<application> --vault <vault> context "installation verification"`. Verify that its JSON
   contains `context` and `maintenance`, then verify that `doctor` reports `fts5: true`, a valid
   strict OKF audit, an existing index, and maintenance state. Do not create operating-system tasks
   unless the human explicitly requests unattended scheduling.
9. Report the vault path, application path, verification result, and any limitation. The protocol
   works with any local command-capable agent regardless of model provider. Do not claim that a
   browser-only chat interface can access local files without a local integration.

## Portable export and migration

When the human asks for an export, first run `reconcile`, then run:

```text
<application> --vault <vault> bundle export <private-destination.zip>
```

Choose a destination outside the vault. Report the final path, SHA-256, file count, and verification
status. Explain that the ZIP contains private knowledge and is not encrypted automatically.

To restore on another machine, download, verify, and extract the matching application bundle as above,
choose a new path that does not already exist, and run:

```text
<application> --vault <new-vault> bundle restore <portable-bundle.zip>
<application> --vault <new-vault> install
<application> --vault <new-vault> doctor
```

The first command verifies file checksums, safely restores the portable context, audits OKF, and
rebuilds FTS5. `install` then regenerates machine-specific instructions and agent-driven maintenance. Connect the
new managed instruction block to the current agent as in step 7. Never copy an old machine's agent
instructions or search cache as a substitute for this regeneration.

Re-running the same procedure upgrades the complete application bundle and reconciles the vault idempotently. A
dated safety copy is created before any existing Markdown file is migrated.
