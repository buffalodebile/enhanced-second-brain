# Internal engine reference

Most people never need this page. The installing agent connects its instruction mechanism so
maintenance advances naturally with agent requests.

The standalone application exposes a small internal interface for AI tools, automation, recovery,
and development:

```text
enhanced-second-brain init | install | doctor
enhanced-second-brain context "<user request>"
enhanced-second-brain okf migrate|audit
enhanced-second-brain index update|query|status|rebuild
enhanced-second-brain page read|upsert
enhanced-second-brain usage record
enhanced-second-brain score
enhanced-second-brain prune candidates|apply|restore
enhanced-second-brain reconcile
enhanced-second-brain maintenance run|status|review
enhanced-second-brain benchmark
enhanced-second-brain backup
enhanced-second-brain bundle export|restore
```

Every operation accepts a vault through `--vault`, `ESB_VAULT_PATH`, or the nearest
`second-brain.toml`. This is an implementation interface, not another dependency or service. The
application is invoked only when an agent request or optional scheduled maintenance needs it; it does not remain
running in the background.
