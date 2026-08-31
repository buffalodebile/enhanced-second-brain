# Enhanced Second Brain

[![CI](https://github.com/buffalodebile/enhanced-second-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/buffalodebile/enhanced-second-brain/actions/workflows/ci.yml)

**Give your AI a memory you own.**

Enhanced Second Brain turns a folder of Markdown notes into a private memory for AI tools such as
Codex. Your AI can find past decisions, reuse what you learned, and keep the folder healthy without
you manually sorting everything.

Your notes stay ordinary files on your computer. No cloud database, GPU, vector model, Obsidian
plugin, or always-running server is required.

## Why use it?

- **Stop repeating yourself.** Your agent can recover relevant decisions and context from previous
  work.
- **Find the right note quickly.** Search is local, lightweight, and updated when files change.
- **Keep the useful knowledge.** Real usage helps rank pages; old low-value pages are archived, not
  deleted.
- **Take it anywhere.** The source of truth is a portable folder of readable Markdown files.
- **Avoid lock-in.** Obsidian is a nice optional interface, not a requirement.

Karpathy's [LLM Wiki idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
describes knowledge as a persistent artifact that compounds instead of being rediscovered in every
chat. Enhanced Second Brain packages that idea into an installable, automatically maintained
system.

## Install

You only need [Python 3.11+](https://www.python.org/downloads/). Then run:

```bash
python -m pip install --user "https://github.com/buffalodebile/enhanced-second-brain/releases/download/v0.1.1/enhanced_second_brain-0.1.1-py3-none-any.whl"
python -m enhanced_second_brain --vault ~/second-brain install
```

On Windows, use `py` instead of `python` if needed:

```powershell
py -m pip install --user "https://github.com/buffalodebile/enhanced-second-brain/releases/download/v0.1.1/enhanced_second_brain-0.1.1-py3-none-any.whl"
py -m enhanced_second_brain --vault "$HOME\second-brain" install
```

Already have notes? Replace `~/second-brain` with their folder. The installer makes a safety copy
before changing existing Markdown.

That is the whole setup. Restart your local AI agent once, then keep working normally. There is no
skill to invoke and no server to start by hand.

> Today the automatic global connection is built for Codex. Claude Code and other local agents get
> vault instructions and can use the same local bridge, but their global configuration may require
> a one-time connection. Browser-only chats cannot read files stored on your computer.

## What happens automatically?

```text
Your Markdown notes -> fast local search -> useful context for your AI
          ^                                      |
          `------ update, score, archive --------'
```

The installer:

1. creates or adopts your notes folder;
2. makes every note portable and machine-readable;
3. builds the local search index;
4. connects the folder to supported agents;
5. schedules maintenance and reversible archival.

After that, new and edited notes are picked up incrementally. Daily maintenance checks the folder;
monthly maintenance moves cold, low-value pages into a dated archive. It never automatically
deletes your knowledge. Remote backup remains off until you explicitly choose a private Git
repository.

## Why is it "enhanced"?

A normal notes folder stores documents. Enhanced Second Brain adds the parts needed for reliable AI
memory:

| Normal notes | Enhanced Second Brain |
|---|---|
| Files are manually searched | The agent retrieves relevant context locally |
| Notes slowly become stale | Existing pages can be updated and checked |
| Every page looks equally useful | Actual use influences ranking |
| Cleanup risks deleting knowledge | Cold pages move to a reversible archive |
| Moving tools can break the system | Markdown remains the portable source of truth |

## Under the hood (optional)

You do not need to understand this section to use the tool.

- **OKF v0.2** gives notes a consistent, portable structure.
- **SQLite FTS5** provides fast keyword search without embeddings, a GPU, or a background database
  service.
- **A link graph** answers relationship and multi-step questions only when needed.
- **Local usage signals** improve ranking without storing your prompts.
- **MCP stdio** is an optional private pipe between an agent and the tool. It is not a web server,
  opens no port, and is started by the agent only when needed.

FTS5 is the best default for this project's lightweight, local-first goal; it is not universally
better than semantic search. A benchmark is included so you can test retrieval on your own notes.

## Learn more

- [How agents connect](docs/agent-and-mcp.md)
- [How search and benchmarks work](docs/retrieval-and-benchmarks.md)
- [Automatic maintenance](docs/automation.md)
- [Portable note format](docs/okf-profile.md)
- [Private backup and restore](docs/backup-restore.md)
- [Privacy and threat model](docs/threat-model.md)
- [Troubleshooting](docs/troubleshooting.md)
- [CLI reference](docs/cli.md)

Enhanced Second Brain is an early public release. Back up an important folder before adopting or
migrating it. Licensed under Apache-2.0.
