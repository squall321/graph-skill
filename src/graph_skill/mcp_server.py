"""MCP stdio server. Thin adapter: registers TOOLS and dispatches to tools.DISPATCH."""

from __future__ import annotations

import asyncio
import json

from . import tools


def _build_server():
    from mcp.server import Server
    from mcp.types import TextContent, Tool

    server = Server("graph-skill")

    @server.list_tools()
    async def list_tools():  # noqa: D401
        return [
            Tool(name=t["name"], description=t["description"], inputSchema=t["inputSchema"])
            for t in tools.TOOLS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        fn = tools.DISPATCH.get(name)
        if fn is None:
            result = {"error": f"unknown tool: {name}"}
        else:
            try:
                result = fn(arguments or {})
            except Exception as e:  # surface as data, never crash the server
                result = {"error": type(e).__name__, "message": str(e)}
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    return server


async def _serve():
    from mcp.server.stdio import stdio_server

    server = _build_server()
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


def main():
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
