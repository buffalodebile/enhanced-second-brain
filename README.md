# Enhanced Second Brain

[![CI](https://github.com/buffalodebile/enhanced-second-brain/actions/workflows/ci.yml/badge.svg)](https://github.com/buffalodebile/enhanced-second-brain/actions/workflows/ci.yml)

## Give any local AI a memory that survives the chat

Every new conversation starts from zero. You repeat your preferences, projects, and decisions, while
useful context slowly disappears into old chats and scattered notes.

Enhanced Second Brain turns a folder of portable knowledge files into a private memory that any
local AI agent can search, maintain, and keep tidy. It is provider-neutral: the same files and the
same single `context` command work with local agents powered by OpenAI, Anthropic, Google, open
models, or future models. The model can change while your context stays yours.

## Installation: give the job to your agent

Send this message to any local AI agent that can access files and run commands:

> Install Enhanced Second Brain from https://github.com/buffalodebile/enhanced-second-brain.
> Follow AGENT_INSTALL.md, use my existing notes folder if I provide one, and verify everything.

That is the human installation flow. The agent detects the machine, downloads one verified
self-contained application bundle, adopts or creates the knowledge folder, builds search, connects its own
persistent instructions, and runs a health check. Maintenance then happens naturally on future
agent requests; no Windows task, cron job, or background service is created by default.

There is no Windows installer to click and no runtime, package manager, plugin, or database service
for the human to configure. The bundle is a normal ZIP that the agent verifies and extracts; its
small runtime directory is what avoids re-extracting a large single-file program on every request.

## What you gain

- **Less repetition** — previous decisions and project context can be recovered before answering.
- **Faster retrieval** — search opens the few useful notes instead of scanning the whole folder.
- **Cleaner memory** — new and edited files are indexed automatically; cold notes are archived,
  never deleted.
- **Privacy** — notes, usage signals, and search stay on the machine.
- **Freedom and context sovereignty** — the memory belongs to you, not to a model account. Export
  it as one standard ZIP, move it to another machine, open it in another editor, or connect it to
  another local AI.

## Your context, in one portable file

Ask your local agent:

> Export my Enhanced Second Brain as one portable bundle, verify it, and tell me where you saved it.

The resulting `.zip` contains the current OKF Markdown knowledge, reversibly archived notes,
attachments, local settings, and usage history. Every file has a SHA-256 checksum in a small
manifest. It does **not** contain the disposable FTS5 index, Git internals, editor state, or
machine-specific agent instructions. Those are rebuilt for the destination machine.

To move it, copy that ZIP to a private drive, encrypted storage, or another computer. Then give the
repository URL and the ZIP to any supported local agent and say:

> Restore this Enhanced Second Brain bundle into my notes folder, reconnect automatic maintenance,
> and run the health check.

The agent verifies every file, rejects unsafe paths or modified content, restores into a new folder,
audits OKF, rebuilds search, and regenerates local integration. Without the toolkit, the ZIP is
still readable with any ordinary archive tool because the knowledge remains UTF-8 Markdown. See
[Context sovereignty and portable export](docs/context-sovereignty.md) for the exact contents,
commands, migration flow, security limits, and difference between export and backup.

## Measured result

On September 1, 2026, we measured 60 searches across **500 OKF Markdown notes** on Windows 11 with
an Intel Core i7-13620H. Enhanced Second Brain found the right note every time and took about
180 milliseconds, compared with about 225 milliseconds when rereading the whole folder.

| Setup | Did it find the right note? | Typical search time | In plain English |
|---|---:|---:|---|
| AI without access to the notes | 0/60 | Not comparable | It cannot remember private information it cannot see. |
| Read the whole Markdown folder every time | 60/60 | About 225 ms | Opens and checks all 500 notes again. |
| **Enhanced Second Brain** | **60/60** | **About 180 ms** | Finds the few notes most likely to contain the answer. |

In plain English: the useful note appeared about **45 milliseconds sooner**, which was **about 20%
less searching time** in this test. More importantly, the AI was shown at most five likely notes
instead of having to inspect all 500. It gets to the useful context with less irrelevant text and
less work. The first setup took 3.9 seconds once; after that, only changed notes needed updating.

This does not mean every complete AI answer will be 20% faster. Writing the answer, network speed,
computer speed, and the contents of the notes also take time. The result only measures how quickly
the system found the right local note. See the [method and exact result](docs/comparison-benchmark-2026-09-01.md),
then test your own notes before making a broader claim.

A same-machine scaling follow-up found 24.1% less retrieval time at 500 notes and 23.5% at 1,000.
At 2,500 notes, the current safety-first freshness scan made the FTS5 path 12.9% slower than a warm
full-folder scan. Enhanced Second Brain is therefore optimized for ordinary personal vaults, not
claimed as the fastest possible engine at every corpus size. The exact runs and limitation are in
the [scaling results](docs/comparison-benchmark-2026-09-01.md#scaling-follow-up).

## Markdown and OKF are used together

OKF does not replace Markdown. [Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
defines a knowledge bundle as a directory of Markdown files with YAML metadata at the top.

- **Markdown** is the readable file and its content: headings, paragraphs, lists, tables, and links.
- **OKF** is the portable contract around that content: type, title, description, sources,
  provenance, generation time, and lifecycle.

In short: Markdown is how the knowledge is written; OKF is how humans and machines agree on what
that knowledge means. The same `.md` file provides both.

```markdown
---
type: Decision
title: Keep search local
description: Use a disposable local index over portable knowledge files.
tags: [architecture, privacy]
sources:
  - resource: notes/architecture-review.md
generated: {by: process:enhanced-second-brain, at: 2026-09-01T00:00:00Z}
status: stable
---

# Keep search local

The knowledge files remain authoritative. The search database can always be rebuilt.
```

## What FTS5 does

FTS5 is SQLite's full-text search engine. It breaks titles, tags, summaries, headings, and body text
into searchable terms, keeps an inverted index, and ranks matches with BM25 relevance.

When a query arrives, Enhanced Second Brain checks which files are new, changed, renamed, or gone.
Only that delta is reindexed; unchanged files are not reparsed. Search then returns a small ranked
set for the agent to read. The index is disposable: delete it and it rebuilds from the OKF Markdown
files. No GPU, embeddings, network request, or continuously running process is involved.

## How the memory stays current

### During normal work

At the start of each request, the agent runs one local command: `context`. That command performs a
tiny maintenance check, updates changed files in FTS5, searches the request, returns likely pages,
and records which results were shown. The agent then reads only relevant pages, records those it
actually uses, and distills durable new knowledge back into the right page. Raw conversation text is
not blindly copied into the knowledge base.

An injected search result counts `0.25`, an opened page counts `1`, and a page actually used in an
answer counts `2`. Older activity gradually loses weight, so something that was popular years ago
does not stay permanently important. Links, confidence, importance tier, freshness, frequency, and
last use are combined into the page's utility score.

### Automatic catch-up

The first `context` call after 24 hours—or after 50 interactions—runs a short local reconciliation:

1. brings new or edited Markdown into the OKF profile;
2. validates required metadata and source structure;
3. synchronizes and verifies the FTS5 index;
4. recalculates page utility from real usage.

Most requests only read one small state file, so there is no heavy maintenance on every prompt. The
process does not invent facts or rewrite meaning without a source and an agent judgment.

### Agent-reviewed cleanup

Pages become archive candidates only after at least 240 days without use, low effective usage, a
minimum age, and a cold utility score. Important, verified, confidential, hub, and sufficiently
linked pages are protected. On the first request after 30 days, the agent reads each candidate and
its relationships before selecting what can safely move. Eligible pages go to a dated archive and
can be restored; automatic deletion is never used.

Operating-system scheduling remains an explicit reliability option for unattended machines. It is
not part of the default installation.

There is no universal API that can force every possible LLM website to access local files. “Any
local AI” therefore means any agent application that can read files, run a command, and retain a
persistent instruction. The engine itself contains no model- or provider-specific adapter.

## Why this stack

[Karpathy's LLM Wiki idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
is powerful because knowledge is compiled and maintained once instead of rediscovered for every
question. Enhanced Second Brain adds a portable OKF contract, fast local retrieval, usage-aware
maintenance, and reversible cleanup while preserving that simple model.

SQLite FTS5 is deliberately the default because it is mature, embedded, cross-platform, and
zero-configuration. The [technical overview](docs/technical-overview.md) explains the database choice
and when a replicated alternative would make sense.

The ingredients are not unprecedented. Other projects already provide Markdown personal wikis,
semantic second brains, or persistent agent memory. The contribution here is a deliberately small,
provider-neutral combination focused on portable OKF files, zero-model lexical retrieval,
usage-aware reversible cleanup, and one-file export. See [what is actually distinctive](docs/positioning-and-novelty.md).

The normal `context` path is also optimized for repeated agent requests: it uses one process, one
SQLite connection, one locked telemetry append, and skips excluded directories during freshness
checks. The release uses a self-contained directory bundle rather than a compressed one-file
executable, because repeatedly unpacking that executable was much slower. See the
[runtime benchmark and exact scope](docs/runtime-benchmark-2026-09-01.md).

## Limits

- A local agent needs filesystem and command access. A browser-only chat cannot silently read local files.
- Lexical search can miss paraphrases that share no useful vocabulary; benchmark your own corpus.
- Obsidian is optional and remains only an interface for the same portable files.
- Remote backup is opt-in and must point to a private destination.
- A portable ZIP is not encrypted automatically; protect it like any private copy of your memory.

Apache-2.0 licensed.
