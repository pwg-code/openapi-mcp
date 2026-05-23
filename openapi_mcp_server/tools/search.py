"""search_endpoints tool."""

from __future__ import annotations

from openapi_mcp_server.registry import ProjectRegistry


async def handle(registry: ProjectRegistry, arguments: dict) -> str:
    project = arguments.get("project", "")
    query = arguments.get("query", "")
    method = arguments.get("method")
    tag = arguments.get("tag")
    limit = arguments.get("limit", 10)

    index = registry.get_index(project)
    if index is None:
        available = ", ".join(registry.get_project_names())
        return f"Error: Project '{project}' not found. Available: {available}"

    result = index.search(query=query, method=method, tag=tag, limit=limit)
    return result.model_dump_json(indent=2)
