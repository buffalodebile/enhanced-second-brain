# Privacy and threat model

## Protected assets

- Markdown knowledge and its Git history.
- The usage ledger, which reveals interests and activity timing.
- The FTS database, which contains searchable copies of indexed text.
- Local paths and AI configuration.

## Expected trust boundary

The operator and local OS account are trusted. The vault, FTS5 cache, and standalone application remain local. A real remote backup is private and access-controlled. The public toolkit repository contains no user vault.

## Main risks and controls

| Risk | Control |
|---|---|
| Publishing personal knowledge | Keep real vaults in separate private repositories; review an explicit allowlist before publication. |
| Cached confidential text | Ignore `_meta/cache/`, keep it on local storage, rebuild rather than transfer it. |
| Prompt leakage | Usage telemetry never stores prompt or answer text. |
| Path traversal | All page and usage paths are resolved and confined to the vault. |
| Destructive cleanup | Strict eligibility, hard protections, move-only archives, explicit restore. |
| Dirty backup corrupting work | Temporary Git index; real index, worktree, and `HEAD` remain untouched. |
| Credentials in snapshots | Secret-like filename refusal plus repository secret scanning and push protection. |
| Vault sent to a public remote | Agent-driven or scheduled backup requires explicit `backup.enabled = true`; a URL alone is never treated as proof of privacy. |
| Application supply chain | The installing agent downloads one versioned application ZIP and verifies it against the release checksum before extraction. CI builds, packages, extracts, and executes every operating-system artifact. Review the public build workflow when the environment requires stronger provenance. |

Do not place raw secrets in Markdown. Secret scanners cannot prove that prose contains no sensitive business information.
