# Agent and MCP integration

Agents can call `esb` directly or connect to its local MCP stdio bridge. No provider-specific SDK is required. `esb install` writes vault-level `AGENTS.md` and `CLAUDE.md`, a project-scoped `.codex/config.toml`, and a managed global Codex instruction block. Codex can therefore query the selected vault from other repositories without an Agent Skill. Existing instruction content is preserved.

Codex reads project-scoped `.codex/config.toml` only for trusted projects. Trusting the vault is an intentional one-time Codex security decision; the installer does not bypass it. The global instruction block still provides the zero-skill CLI workflow outside the vault. Restart an already-running agent session after installation so it reloads instructions.

## MCP tools

- `search`
- `read_page`
- `graph_query`
- `status`
- `record_citation`
- `upsert_page`

Read tools are enabled by default. Although citation telemetry does not change Markdown, it changes local state and is therefore treated as a write. Both write tools require `mcp.allow_writes=true`.

Example client configuration:

```json
{
  "mcpServers": {
    "enhanced-second-brain": {
      "command": "esb",
      "args": ["--vault", "/absolute/path/to/vault", "mcp"]
    }
  }
}
```

MCP means Model Context Protocol. Keep the transport on stdio. It is a child process, not a persistent web server: no TCP port is opened and it exits with the client. Remote HTTP exposure, authentication, and multi-user authorization are out of scope for v0.1.

An agent should search first, read only useful pages, and record a citation only for pages that materially support its answer. Pure browser chats cannot access local files unless the host product deliberately provides a filesystem, command, or MCP bridge.

Codex officially layers global and project `AGENTS.md` files before work and supports project-scoped MCP configuration for trusted projects. The installer uses those supported mechanisms rather than installing a global skill: [AGENTS.md documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md) and [Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
