# Enhanced Second Brain

[![CI](https://github.com/buffalodebile/enhanced-second-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/buffalodebile/enhanced-second-brain/actions/workflows/ci.yml)

## Give your AI a memory that survives the chat

Every new AI conversation starts from zero. You repeat your preferences, your projects, and the
decisions you already made.

Enhanced Second Brain turns ordinary Markdown files into a private memory that Codex can search,
update, and clean up automatically.

## Install in a few minutes

### Windows

1. [Download the Windows installer](https://github.com/buffalodebile/enhanced-second-brain/releases/latest/download/install.cmd).
2. Double-click `install.cmd`.
3. Restart Codex once.

### macOS or Linux

Paste this one command into Terminal, then restart your AI tool:

```bash
curl -fsSL https://github.com/buffalodebile/enhanced-second-brain/releases/latest/download/install.sh | sh
```

The installer creates `SecondBrain` in your home folder and adds one standalone local app. There is
no separate Python runtime, package manager, skill, plugin, agent, MCP server, database server, or
command-line tool to install.

Already have a notes folder? See [use an existing folder](docs/troubleshooting.md#use-an-existing-notes-folder).

## What you get

- **Less repetition** — your AI can recover previous decisions and project context.
- **Faster answers** — it searches the useful notes instead of scanning everything.
- **A cleaner memory** — new and edited files are picked up automatically; cold notes are archived,
  never deleted.
- **Privacy** — your notes and search stay on your computer.
- **Freedom** — everything remains readable Markdown that you can copy, back up, or open in
  Obsidian.

## The whole system

1. **Markdown + OKF** keeps every note structured, readable, and portable.
2. **FTS5** finds the useful notes locally without embeddings or a GPU.
3. **Daily maintenance** picks up new and edited notes and repairs their structure.
4. **Monthly cleanup** moves cold, low-value notes to a reversible archive.

Codex is connected during installation, so you keep working normally. No extra agent is installed.

## Why "Enhanced"?

[Karpathy's LLM Wiki idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
is simple and powerful: let the AI maintain a persistent wiki instead of rediscovering the same
documents for every question.

Enhanced Second Brain makes that idea ready for daily use with only two moving parts: portable OKF
notes and a disposable FTS5 search index. Usage-aware ranking and reversible cleanup run
automatically around them.

There is no cloud database, subscription, GPU, vector model, or always-running service.

## Good to know

- Obsidian is optional. It is only an interface for the same Markdown files.
- Automatic global memory currently works with Codex. Other local AI tools may need a one-time
  connection to the same folder.
- Browser-only chats cannot silently read files stored on your computer.
- Back up important notes before migrating an existing folder.

Want the implementation details? Read the [technical overview](docs/technical-overview.md).

Apache-2.0 licensed.
