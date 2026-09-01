# Context sovereignty and portable export

## What context sovereignty means here

Your second brain is not stored inside a model account, a proprietary database, or a hosted search
service. The authoritative copy is a folder of UTF-8 Markdown files structured with OKF metadata.
You decide where that folder and its copies live, which agent may read them, and when they leave the
machine.

This gives you four practical freedoms:

1. **Inspect it:** open every knowledge page with an ordinary text editor.
2. **Move it:** transfer one standard ZIP across Windows, macOS, and Linux.
3. **Change tools:** keep the same files when changing editor, model, or local agent.
4. **Rebuild it:** recreate search and maintenance from the knowledge files instead of preserving a
   fragile machine-specific database.

The toolkit improves access to the context; it never becomes the owner of that context.

## What the portable bundle contains

| Included | Why it travels |
|---|---|
| Current OKF Markdown pages | They are the readable source of truth. |
| `_archives/pruned/` | Archived knowledge remains reversible and is still yours. |
| Attachments and referenced local files | A diagram, image, or document may be part of the knowledge. |
| `second-brain.toml` | Retrieval, usage, and archival policy should survive the move. |
| `_meta/usage.jsonl` | Usage history affects utility and future archival decisions. It contains event time, type, path, and weight—not prompts or answers. |
| `_meta/maintenance.json` | Portable counters and timestamps let another agent continue the maintenance cadence. |
| `enhanced-second-brain-bundle.json` | The manifest records every portable path, byte size, and SHA-256 checksum. It contains no absolute source path. |

## What it deliberately leaves behind

| Excluded | What happens after the move |
|---|---|
| `_meta/cache/` | FTS5 is rebuilt from the Markdown pages. |
| `_meta/utility.json` | Utility scores are recalculated from pages and usage history. |
| `.git/` and `.gitignore` | Git history belongs to private backup, not the portable knowledge contract. |
| `.obsidian/` | Editor layout and plugins are optional machine preferences. |
| Local agent instruction files | Agent commands contain local executable and vault paths, so fresh instructions are generated. |
| Temporary locks and install safety copies | They are local operating state, not knowledge. |
| Symbolic links and secret-like files | Export fails closed instead of following a link outside the vault or accidentally packaging credentials. |

This distinction matters. The ZIP contains the **portable knowledge context**, including archived
knowledge and the usage signals needed for governance. It does not claim to contain operating-system
tasks, Git history, editor preferences, passwords, or a copy of the model itself.

## Export with a local agent

The normal human flow is one request:

> Export my Enhanced Second Brain as one portable bundle, verify it, save it in my private backup
> folder, and report the path and checksum.

The agent should follow `AGENT_INSTALL.md`. Internally, it first reconciles new and edited notes,
then invokes the standalone application:

```text
<application> --vault <vault> reconcile
<application> --vault <vault> bundle export <destination.zip>
```

The destination must be outside the vault and must not already exist. A directory may be supplied;
the application then creates a timestamped `enhanced-second-brain-<date>.zip` inside it. Refusing to
overwrite an existing file prevents an agent from silently destroying the previous portable copy.

Before creating the bundle, the application:

1. performs a strict OKF audit;
2. refuses symbolic links, secret-like filenames, and paths that would not survive all supported
   operating systems;
3. reads every selected file once into the export snapshot;
4. records its relative path, size, and SHA-256 in the manifest;
5. writes a compressed standard ZIP to a temporary file;
6. atomically moves the completed file into place;
7. hashes the final ZIP and reports that checksum, file count, knowledge-page count, and size.

No absolute source folder, account name, search database, prompt, or answer is written into the
manifest. Relative Markdown links therefore keep working after the folder moves.

## Transfer it anywhere

Copy the ZIP using any storage you control: an external drive, an encrypted archive, a private cloud
folder, a private network share, or direct machine-to-machine transfer. It is a normal ZIP, so no
Enhanced Second Brain service is required to store it.

The bundle is **not encrypted by Enhanced Second Brain**. Anyone who obtains it may be able to read
your notes and infer activity timing from the usage ledger. Encrypt the destination or the bundle at
the storage layer, restrict access, and never publish a real context bundle in the public toolkit
repository.

If a web AI accepts file uploads, you may manually provide selected extracted Markdown pages. A
browser-only chat still cannot continuously search or maintain a local folder by itself. Full
automatic use requires a local agent with permission to access files and run the standalone
application.

## Restore on another machine

Give the repository URL and bundle to a local agent on the destination machine:

> Restore this Enhanced Second Brain bundle into a new notes folder. Verify every file, reconnect
> automatic maintenance for this machine, rebuild search, and run the health check.

The agent downloads and verifies the appropriate standalone release, then runs:

```text
<application> --vault <new-vault> bundle restore <portable-bundle.zip>
<application> --vault <new-vault> install
<application> --vault <new-vault> doctor
```

`<new-vault>` must not already exist. Restore is intentionally non-merge and non-overwriting. The
application then:

1. opens the ZIP without trusting its filenames;
2. rejects absolute paths, `..` traversal, backslashes, duplicated entries, extra files, and
   machine-specific paths;
3. verifies every size and SHA-256 against the manifest;
4. extracts into a temporary sibling directory;
5. runs the strict OKF audit before promoting that directory to the final vault path;
6. rebuilds the local FTS5 index from Markdown;
7. lets `install` generate paths, persistent agent instructions, and agent-driven maintenance for
   the new machine;
8. uses `doctor` to confirm OKF, FTS5, and the index.

The original bundle remains unchanged. If validation fails, the final destination is not created.

## Read or migrate without the toolkit

The ZIP can be opened with Windows Explorer, macOS Finder, `unzip`, 7-Zip, or any compatible archive
library. Extract it and open the `.md` files in a text editor, Obsidian, another Markdown knowledge
tool, or a program that understands OKF frontmatter. The JSON manifest is documentation and an
integrity map; it does not encrypt or hide the pages.

Another tool does not need to reproduce FTS5, usage scoring, or automatic archival in order to read
the knowledge. Those features are Enhanced Second Brain's operating layer. Markdown plus OKF is the
portable layer that prevents lock-in.

## Export versus private Git backup

Use both when the context matters:

- **Portable bundle:** one self-contained transfer file; easy to move and inspect; no Git history.
- **Private Git backup:** version history, validated `main`, and the latest isolated dirty snapshot;
  requires a private remote and Git-aware recovery.

The bundle answers “Can I take my current context elsewhere?” Git backup answers “Can I recover an
older state after loss or a bad edit?” Neither should be public, and neither replaces an independent
encrypted backup policy.
