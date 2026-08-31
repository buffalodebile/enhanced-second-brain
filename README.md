# Enhanced Second Brain

[![CI](https://github.com/buffalodebile/enhanced-second-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/buffalodebile/enhanced-second-brain/actions/workflows/ci.yml)

## Give your AI a memory that survives the chat

Every new AI conversation starts from zero. You repeat your preferences, your projects, and the
decisions you already made.

Enhanced Second Brain gives local AI tools such as Codex a private memory made of ordinary
Markdown files. It finds useful context automatically and keeps that memory tidy over time.

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

The installer creates `SecondBrain` in your home folder. It also handles search and automatic
maintenance. You do not need to install Python, Git, a skill, or a server. The tool keeps its own
small runtime in a separate folder.

Already have a notes folder? See [use an existing folder](docs/troubleshooting.md#use-an-existing-notes-folder).

## What you get

- **Less repetition** — your AI can recover previous decisions and project context.
- **Faster answers** — it searches the useful notes instead of scanning everything.
- **A cleaner memory** — new and edited files are picked up automatically; cold notes are archived,
  never deleted.
- **Privacy** — your notes and search stay on your computer.
- **Freedom** — everything remains readable Markdown that you can copy, back up, or open in
  Obsidian.

## How it works

1. You work with your AI as usual.
2. Useful knowledge is saved into your Second Brain.
3. Future conversations retrieve only the context they need.

The result improves over time instead of disappearing at the end of every chat.

## Why "Enhanced"?

[Karpathy's LLM Wiki idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
is simple and powerful: let the AI maintain a persistent wiki instead of rediscovering the same
documents for every question.

Enhanced Second Brain makes that idea ready for daily use. It adds quick local search, portable
notes, usage-aware ranking, automatic health checks, and reversible cleanup — while staying light
enough for an ordinary laptop.

There is no cloud database, subscription, GPU, vector model, or always-running service.

## Good to know

- Obsidian is optional. It is only an interface for the same Markdown files.
- Automatic global memory currently works best with Codex. Other local agents can use the same
  folder, but may need a one-time connection.
- Browser-only chats cannot silently read files stored on your computer.
- Back up important notes before migrating an existing folder.

Want the implementation details? Read the [technical overview](docs/technical-overview.md).

Apache-2.0 licensed.
