# Usage scoring and reversible archival

The append-only `_meta/usage.jsonl` ledger distinguishes weak exposure from actual use:

| Event | Weight | Meaning |
|---|---:|---|
| `injected` | 0.25 | Search result returned to an agent |
| `opened` | 1 | Page body read |
| `cited` | 2 | Agent explicitly records use in an answer |

Writes use a cross-platform file lock. The ledger contains timestamp, event, relative path, and weight—never the prompt or answer text. It is ignored on the main branch and may be included only in a private backup snapshot.

Utility combines tier, confidence, backlinks, freshness, and effective usage into a generated score. It never updates page frontmatter, because that would make telemetry look like knowledge freshness.

## Candidate policy

A page qualifies only when all conditions hold:

- no use for at least 240 days;
- effective usage at most 3;
- page age at least 60 days;
- utility at or below the cold threshold;
- no hard protection.

Hard protections cover core, verified, confidential, rejected, project-hub, and sufficiently linked pages. `esb prune candidates` is always read-only. `esb prune apply path.md` performs a fresh strict OKF audit and eligibility check, adds archive metadata, then moves content to `_archives/pruned/<date>/`. An explicitly scheduled policy may use `esb prune apply --all-candidates`; it still revalidates every page and only moves eligible content. `esb prune restore` moves one page back. No command automatically deletes knowledge.
