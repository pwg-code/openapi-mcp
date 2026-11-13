"""search_endpoints tool."""

from __future__ import annotations

from openapi_mcp_server.models import ProjectStatus
from openapi_mcp_server.registry import ProjectRegistry
from openapi_mcp_server.tools.notready import not_ready_response


async def handle(registry: ProjectRegistry, arguments: dict) -> str:
    project = arguments.get("project", "")
    query = arguments.get("query", "")
    method = arguments.get("method")
    tag = arguments.get("tag")
    limit = arguments.get("limit", 10)

    entry = registry.get_entry(project)
    if entry is None:
        available = ", ".join(registry.get_project_names())
        return f"Error: Project '{project}' not found. Available: {available}"

    if entry.status != ProjectStatus.LOADED:
        not_ready = not_ready_response(registry, project)
        if not_ready:
            return not_ready

    index = registry.get_index(project)
    if index is None:
        return f"Error: Project '{project}' not loaded. Call refresh_spec to reload it."

    result = index.search(query=query, method=method, tag=tag, limit=limit)
    return result.model_dump_json(indent=2)
