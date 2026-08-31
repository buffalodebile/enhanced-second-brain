from __future__ import annotations

import asyncio

import pytest
from conftest import write_page

from enhanced_second_brain.mcp_server import create_server


def test_in_memory_mcp_tools_and_disabled_writes(settings, vault) -> None:
    write_page(
        vault,
        "concepts/mcp.md",
        title="MCP note",
        description="Local protocol note",
        body="# MCP note\n\nA stdio protocol example.",
    )
    server = create_server(settings)
    tools = asyncio.run(server.list_tools())
    assert {tool.name for tool in tools} == {
        "search",
        "read_page",
        "graph_query",
        "status",
        "record_citation",
        "upsert_page",
    }
    annotations = {tool.name: tool.annotations for tool in tools}
    assert annotations["search"].read_only_hint is True
    assert annotations["upsert_page"].destructive_hint is True
    result = asyncio.run(
        server.call_tool("search", {"query": "stdio protocol", "limit": 5})
    )
    assert not result.is_error
    from mcp.server.mcpserver.exceptions import ToolError

    with pytest.raises(ToolError, match="writes are disabled"):
        asyncio.run(server.call_tool("record_citation", {"path": "concepts/mcp.md"}))
