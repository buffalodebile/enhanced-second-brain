# Automatic durable-knowledge capture

The portable application includes the hooks. It adds no runtime dependency, model API,
scheduled task, background worker or service. The current agent selects useful knowledge,
reads existing pages and supplies merged content. The hook checks that this work was
considered before the turn ends. Conversations are never copied blindly.

## Native installation

`install` detects existing Codex and Claude Code applications/configuration directories and
adds `UserPromptSubmit`, `Stop` and `SessionEnd` handlers. It preserves unrelated settings,
existing hooks and integrations belonging to another vault. Repeated installation updates
only this vault's entries. Hook detection downloads no application.

```text
esb --vault <vault> hooks install --provider auto
esb --vault <vault> hooks status
esb --vault <vault> hooks uninstall --provider auto
esb --vault <vault> install --no-hooks
```

Use `--provider codex` or `--provider claude` for a specific application. Codex configuration
is `<CODEX_HOME>/hooks.json` (default `~/.codex/hooks.json`); Claude configuration is
`<CLAUDE_CONFIG_DIR>/settings.json` (default `~/.claude/settings.json`). Claude uses exec-form
arguments without shell interpolation. Codex uses a quoted command and a Windows override
invoking PowerShell with encoded literal arguments.

**Review new or changed Codex hooks through `/hooks`.** Installation never changes trust
records or bypasses native review. `doctor` and `hooks status` distinguish detection,
configuration and activation still requiring native review/runtime verification. Application
presence does not prove hook support, sandbox access or policy permission. Verify in a real
session that context appears and an empty checkpoint closes without a reminder. Claude versions
must support exec-form command hooks. Hosts must run this executable and access this vault;
cloud sessions need their own accessible application and vault.

References: [Codex hooks](https://developers.openai.com/codex/hooks),
[Claude Code hooks](https://code.claude.com/docs/en/hooks).

## Capture lifecycle and interface

At prompt submission, the hook calls existing `context` once for the identified event and
injects relevant results, maintenance information and a capture token. The agent does not
repeat context lookup. Replayed identified events and Codex Stop continuation prompts do
not count as extra maintenance turns. Claude supplies no turn id: its adapter uses a prompt
digest and transcript file position without reading or storing transcript text. Without a
position, each submission receives a new token rather than suppressing identical prompts.

Before finishing, the agent checks for decisions, resolved incidents, measured results,
lasting preferences or reusable lessons. It searches/reads existing knowledge and merges
before creating pages. Trivial exchanges and immediately reconstructible code details receive
an empty checkpoint. This small receipt is required even for an idle turn.

```text
esb --vault <vault> page read concepts/decision.md
esb --vault <vault> checkpoint complete --turn-id <injected-token> --input <temporary-file.json>
esb --vault <vault> checkpoint status --turn-id <injected-token>
```

`page read` returns the `sha256` of the exact content snapshot returned. Put the temporary
proposal outside the vault root and delete it after success. The input format is:

```json
{
  "updates": [{
    "path": "concepts/decision.md",
    "expected_sha256": null,
    "metadata": {
      "title": "Keep search local",
      "description": "Portable Markdown remains authoritative.",
      "tags": ["architecture"],
      "sources": [{"resource": "urn:example:architecture-review"}]
    },
    "body": "# Keep search local\n\nThe index is a disposable cache."
  }]
}
```

Use `null` only for a new page and the hash returned by `page read` for an existing page.
`metadata.title`, `metadata.description` and a complete Markdown `body` are required. Omitted
existing metadata is preserved. Sources are merged, extensions retained, `created` preserved,
and `updated`/`generated.at` advanced only on material changes. Relations can be updated
explicitly. Keep relative `.md` body links and never invent verification. An empty receipt
is `{"updates": []}`.

The entire batch is validated before publication. Toolkit writers share a lock and check
expected content hashes; a conflict requires rereading and merging. Atomic replacement is
per file, not an all-files filesystem transaction. A local journal makes partial batches
resumable. Retry the identical proposal after interruption or indexing failure. Already-applied
pages are recognized, and the index is repaired before success. If a conflict requires a revised
proposal, include every page from the applying batch with fresh expected hashes.

Only touched pages are indexed, in one SQLite connection. Unchanged pages keep their bytes
and timestamps. Do not run full `reconcile` after capture. The existing 24-hour/50-user-prompt
maintenance, archive review and opt-in private backup keep their cadence. Pages are saved
locally immediately; capture does not push Git at every turn.

## Missed checkpoints and failures

`Stop` reads small state files and requests one continuation if the checkpoint is missing.
A repeated Stop or `stop_hook_active` never creates another reminder. If capture still fails,
the hook allows closure, warns and retains unfinished work for the next prompt, including
in a new session. `SessionEnd` preserves incomplete state without semantic work after closure.
The next agent can inspect checkpoint status and recover proposals. Lost conversation evidence
must be reported honestly, never invented.

Malformed events/runtime errors warn and let the host continue. Checkpoint commands fail
explicitly and never report success after a validation/indexing error. Local state and recovery
journals are under `_meta/cache/hooks/`, excluded from Git backup, retrieval and portable exports.
They contain identifiers and proposed knowledge, no stored prompts or raw transcripts.
Completed receipts and event identifiers remain as local deduplication state.

## Generic contract for other applications

Call `hook run --provider generic` with JSON on stdin:

```json
{"event":"begin","session_id":"stable-session","event_id":"stable-user-event","prompt":"The user request"}
```

The result contains `action: "allow"`, a `turn_id` capture token and `context` to inject.
Replaying the same session/event returns the same token without repeating lookup/maintenance.
Give each real user request a new event id, including identical text. A technical continuation
retains the original token instead of submitting another begin.

```json
{"event":"end","session_id":"stable-session","turn_id":"returned-token","stop_hook_active":false}
```

An end returns `action: "allow"` with an optional `warning`, or `action: "continue"` with
`reason`. Map continuation to the host's native mechanism. A host without that capability
must show the reminder and rely on next-prompt recovery; immediate enforcement is unavailable.
A `session_end` event needs `session_id` and permits closure. Tokens from another session
are rejected. Codex/Claude adapters return their native JSON output schemas.

## Performance

Run `python scripts/benchmark_hooks.py --pages 500 2500 --repeats 30` and optionally add
`--executable <portable-application>`. Fictional temporary vaults are cleaned after measurement.
Median/P95 are reported separately for idle Stop and one-page capture. Targets: engine idle
P95 below 20 ms and portable idle invocation P95 below 500 ms on the reference machine.
These exclude model work and transport/tool-call latency.

The [October 12 measurements](hooks-benchmark-2026-10-12.md) report engine idle P95 below
2.5 ms and Windows portable idle invocation P95 around 210 ms on both corpus sizes.
