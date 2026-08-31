from __future__ import annotations

from typing import Any

from .config import Settings
from .graph import bridges, clusters, hubs, impact, path
from .service import cite, read_page, search, system_status, upsert_page


def graph_query(settings: Settings, intent: str, **kwargs: Any) -> Any:
    if intent == "path":
        return path(settings.vault, kwargs["source"], kwargs["target"])
    if intent == "impact":
        return impact(
            settings.vault,
            kwargs["page"],
            depth=int(kwargs.get("depth", settings.graph_depth)),
        )
    if intent == "hubs":
        return hubs(settings.vault, limit=int(kwargs.get("limit", 10)))
    if intent == "clusters":
        return clusters(settings.vault)
    if intent == "bridges":
        return bridges(settings.vault, limit=int(kwargs.get("limit", 10)))
    raise ValueError("intent must be path, impact, hubs, clusters, or bridges")


def create_server(settings: Settings):
    try:
        from mcp.server.mcpserver import MCPServer
        from mcp.server.mcpserver.exceptions import ToolError
        from mcp_types import ToolAnnotations
    except ImportError as exc:
        raise RuntimeError(
            "Install MCP support with: pip install 'enhanced-second-brain[mcp]'"
        ) from exc

    server = MCPServer("enhanced-second-brain", title="Enhanced Second Brain")

    read_only = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, open_world_hint=False
    )
    local_write = ToolAnnotations(
        read_only_hint=False, destructive_hint=False, open_world_hint=False
    )
    content_write = ToolAnnotations(
        read_only_hint=False, destructive_hint=True, open_world_hint=False
    )

    @server.tool(name="search", annotations=read_only)
    def search_pages(query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search the local vault with FTS5 and record returned pages as injected."""
        return search(settings, query, limit=limit)

    @server.tool(name="read_page", annotations=read_only)
    def read_page_tool(path: str) -> dict[str, Any]:
        """Read one vault page and record an opened event."""
        return read_page(settings, path)

    @server.tool(name="graph_query", annotations=read_only)
    def graph_query_tool(
        intent: str,
        source: str = "",
        target: str = "",
        page: str = "",
        depth: int = 3,
        limit: int = 10,
    ) -> Any:
        """Run a structural graph query: path, impact, hubs, clusters, or bridges."""
        return graph_query(
            settings,
            intent,
            source=source,
            target=target,
            page=page,
            depth=depth,
            limit=limit,
        )

    @server.tool(name="status", annotations=read_only)
    def status_tool() -> dict[str, Any]:
        """Return local vault and index status."""
        return system_status(settings)

    @server.tool(name="record_citation", annotations=local_write)
    def record_citation(path: str) -> dict[str, Any]:
        """Record that an agent used a page in an answer."""
        if not settings.mcp_allow_writes:
            raise ToolError("MCP writes are disabled; set mcp.allow_writes=true")
        return cite(settings, path)

    @server.tool(name="upsert_page", annotations=content_write)
    def upsert_page_tool(
        path: str,
        title: str,
        description: str,
        body: str,
        tags: list[str] | None = None,
        source: str | None = None,
    ) -> dict[str, Any]:
        """Create or update an Enhanced OKF page when writes are enabled."""
        if not settings.mcp_allow_writes:
            raise ToolError("MCP writes are disabled; set mcp.allow_writes=true")
        return upsert_page(
            settings,
            path,
            title=title,
            description=description,
            body=body,
            tags=tags,
            source=source,
        )

    return server


def run(settings: Settings) -> None:
    create_server(settings).run(transport="stdio")
