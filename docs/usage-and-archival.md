# Usage scoring and reversible archival

The append-only `_meta/usage.jsonl` ledger distinguishes weak exposure from actual use:

| Event | Weight | Meaning |
|---|---:|---|
| `injected` | 0.25 | Search result returned to an agent |
| `opened` | 1 | Page body read |
| `cited` | 2 | Agent explicitly records use in an answer |

Writes use a cross-platform file lock. The ledger contains timestamp, event, relative path, and weight—never the prompt or answer text. It is ignored on the main branch and may be included only in a private backup snapshot.

The ledger keeps lifetime totals, while the utility score uses a 180-day half-life: recent activity
matters more and old activity fades gradually. Utility combines tier, confidence, backlinks,
freshness, decayed effective usage, and last use into a generated score. It never updates page
frontmatter, because that would make telemetry look like knowledge freshness.

## Candidate policy

A page qualifies only when all conditions hold:

- no use for at least 240 days;
- decayed effective usage at most 3;
- page age at least 60 days;
- utility at or below the cold threshold;
- no hard protection.

Hard protections cover core, verified, confidential, rejected, project-hub, and sufficiently linked
pages. Every 30 days, the next `context` call gives the eligible list to the agent. The agent opens each
candidate and checks whether it is obsolete, duplicated, superseded, or still a rare durable
decision. `maintenance review` moves only the selected pages to `_archives/pruned/<date>/` and marks
the review complete even when the correct selection is empty. Restore remains available through the
[internal engine](engine-reference.md). Nothing automatically deletes knowledge.
