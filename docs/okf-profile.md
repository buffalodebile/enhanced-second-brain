# Enhanced OKF profile

Enhanced Second Brain uses [Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) as a portable Markdown convention and adds an explicitly separate governance profile.

## Knowledge fields

Every page must contain:

| Field | Shape |
|---|---|
| `type` | Knowledge object type |
| `title` | Human-readable title |
| `description` | Short retrieval summary |
| `tags` | List of strings |
| `sources` | List of objects containing `resource` |
| `generated` | Object containing `by` and `at` |
| `status` | Current publication/workflow status |

## Enhanced governance extensions

The toolkit also requires `summary`, `category`, `relationships`, `base_confidence`, `lifecycle`, `tier`, `created`, and `updated`. These are **Enhanced Second Brain extensions**, not claims about fields required by the official OKF specification.

`description` and `summary` must match. Body links should use standard relative Markdown links with `.md`. `relationships` may hold typed targets for graph-aware agents.

```markdown
---
type: Concept
title: Offline field notes
description: A capture workflow that remains useful without a network connection.
tags: [workflow, local-first]
sources:
  - resource: urn:example:field-manual
generated:
  by: process:enhanced-second-brain
  at: 2026-01-15T10:00:00+00:00
status: stable
summary: A capture workflow that remains useful without a network connection.
category: concepts
relationships:
  - type: supports
    target: "[[projects/aurora/aurora]]"
base_confidence: 0.9
lifecycle: stable
tier: supporting
created: 2026-01-15T10:00:00+00:00
updated: 2026-01-15T10:00:00+00:00
---

# Offline field notes

See the [Aurora project](../projects/aurora/aurora.md).
```

`esb okf migrate` previews deterministic additions. Add `--write` to update files. Run it again to confirm idempotence, then use `esb okf audit`.
