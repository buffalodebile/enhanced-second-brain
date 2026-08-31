# Agent and MCP integration

Agents call `esb` directly after the standard installation. No provider-specific SDK or Agent Skill
is required. `esb install` writes vault-level `AGENTS.md` and `CLAUDE.md` plus a managed global
Codex instruction block. Codex can therefore query the selected vault from other repositories.
Existing instruction content is preserved.

Restart an already-running agent session after installation so it reloads instructions.

## Optional MCP bridge

MCP is not part of the default installation. The normal automatic Codex workflow does not need it.
Install the easy setup first. Add MCP only if an agent client specifically supports MCP tools.

Windows PowerShell:

```powershell
& "$env:LOCALAPPDATA\EnhancedSecondBrain\runtime\Scripts\python.exe" -m pip install "enhanced-second-brain[mcp] @ https://github.com/buffalodebile/enhanced-second-brain/releases/download/v0.1.2/enhanced_second_brain-0.1.2-py3-none-any.whl"
& "$env:LOCALAPPDATA\EnhancedSecondBrain\runtime\Scripts\esb.exe" --vault "$HOME\SecondBrain" install
```

macOS or Linux:

```bash
~/.local/share/enhanced-second-brain/runtime/bin/python -m pip install \
  "enhanced-second-brain[mcp] @ https://github.com/buffalodebile/enhanced-second-brain/releases/download/v0.1.2/enhanced_second_brain-0.1.2-py3-none-any.whl"
~/.local/share/enhanced-second-brain/runtime/bin/esb --vault ~/SecondBrain install
```

The second command adds the project-scoped `.codex/config.toml` entry. Codex loads that entry only
after the vault is trusted, which is an intentional one-time security decision.

The bridge exposes:

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
