"""get_endpoint_detail tool."""

from __future__ import annotations

from openapi_mcp_server.registry import ProjectRegistry


async def handle(registry: ProjectRegistry, arguments: dict) -> str:
    project = arguments.get("project", "")
    path = arguments.get("path", "")
    method = arguments.get("method", "")

    index = registry.get_index(project)
    if index is None:
        available = ", ".join(registry.get_project_names())
        return f"Error: Project '{project}' not found. Available: {available}"

    endpoint = index.get_by_path_method(path, method)
    if not endpoint:
        return f"Error: Endpoint '{method.upper()} {path}' not found in project '{project}'"

    return endpoint.model_dump_json(indent=2, by_alias=True)
