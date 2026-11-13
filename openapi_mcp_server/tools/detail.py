"""get_endpoint_detail tool."""

from __future__ import annotations

from openapi_mcp_server.models import ProjectStatus
from openapi_mcp_server.registry import ProjectRegistry
from openapi_mcp_server.tools.notready import not_ready_response


async def handle(registry: ProjectRegistry, arguments: dict) -> str:
    project = arguments.get("project", "")
    path = arguments.get("path", "")
    method = arguments.get("method", "")

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

    endpoint = index.get_by_path_method(path, method)
    if not endpoint:
        return f"Error: Endpoint '{method.upper()} {path}' not found in project '{project}'"

    return endpoint.model_dump_json(indent=2, by_alias=True)
