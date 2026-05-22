"""MCP Server entry point using FastMCP."""

from __future__ import annotations

import asyncio
import logging
import sys

from mcp.server.fastmcp import FastMCP

from openapi_mcp_server.models import AppConfig
from openapi_mcp_server.registry import ProjectRegistry
from openapi_mcp_server.refresh import RefreshManager
from openapi_mcp_server.tools import detail, list_projects, list_tags, refresh, search

logger = logging.getLogger(__name__)

mcp = FastMCP("openapi-mcp")

_registry: ProjectRegistry | None = None
_refresh_manager: RefreshManager | None = None


def _get_registry() -> ProjectRegistry:
    if _registry is None:
        raise RuntimeError("Server not initialized")
    return _registry


def _get_refresh_manager() -> RefreshManager:
    if _refresh_manager is None:
        raise RuntimeError("Server not initialized")
    return _refresh_manager


# --- Register Tools ---


@mcp.tool()
async def search_endpoints(project: str, query: str, method: str | None = None, tag: str | None = None, limit: int = 10) -> str:
    """Find API endpoints by keyword. Use this whenever the user asks about any API, endpoint, or REST operation — e.g. "is there an API for X", "find the login endpoint", "what APIs exist for users", "how to call X". Searches paths, summaries, tags, and operationIds. Returns basic info; use get_endpoint_detail for full details."""
    return await search.handle(_get_registry(), {
        "project": project,
        "query": query,
        "method": method,
        "tag": tag,
        "limit": limit,
    })


@mcp.tool()
async def get_endpoint_detail(project: str, path: str, method: str) -> str:
    """Get full details of an API endpoint: parameters, request body schema, and response schemas. Always call this after search_endpoints — the search only returns summaries. You need this to know required/optional parameters, request body fields, and response formats before calling an API. All $ref references are resolved inline."""
    return await detail.handle(_get_registry(), {
        "project": project,
        "path": path,
        "method": method,
    })


@mcp.tool(name="list_projects")
async def list_projects_tool() -> str:
    """List all loaded OpenAPI projects with name, version, and endpoint count. Call this first when you don't know the project name — e.g. "what APIs are available", "show me the projects", "which services do we have". You need the project name to call any other tool."""
    return await list_projects.handle(_get_registry(), {})


@mcp.tool(name="list_tags")
async def list_tags_tool(project: str) -> str:
    """List API tags (groups like 'Users', 'Orders', 'Auth') with endpoint counts. Use when the user wants to browse APIs by category — e.g. "what groups of APIs exist", "show me user-related endpoints", "what categories are there". Use tag names to filter search_endpoints."""
    return await list_tags.handle(_get_registry(), {"project": project})


@mcp.tool()
async def refresh_spec(project: str | None = None) -> str:
    """Reload OpenAPI spec(s) from source. Call when the API may have changed — e.g. "the endpoint is missing", "API was updated", "refresh the spec", or search_endpoints returns unexpected results."""
    return await refresh.handle(_get_registry(), _get_refresh_manager(), {
        "project": project,
    })


# --- Server Lifecycle ---


async def run_server(config: AppConfig) -> None:
    global _registry, _refresh_manager

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    _registry = ProjectRegistry(config)
    await _registry.load_all()

    _refresh_manager = RefreshManager(_registry)
    _refresh_manager.start()

    loaded = sum(1 for n in _registry.get_project_names() if _registry.get_entry(n) and _registry.get_entry(n).status.value == "loaded")
    total = len(_registry.get_project_names())
    if loaded < total:
        logger.warning(f"OpenAPI MCP Server ready: {loaded}/{total} project(s) loaded successfully")
    else:
        logger.info(f"OpenAPI MCP Server ready with {total} project(s)")

    try:
        await mcp.run_stdio_async()
    finally:
        if _refresh_manager:
            _refresh_manager.stop()
