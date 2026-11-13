"""list_tags tool."""

from __future__ import annotations

from openapi_mcp_server.models import ListTagsResult, ProjectStatus
from openapi_mcp_server.registry import ProjectRegistry
from openapi_mcp_server.tools.notready import not_ready_response


async def handle(registry: ProjectRegistry, arguments: dict) -> str:
    project = arguments.get("project", "")

    entry = registry.get_entry(project)
    if entry is None:
        available = ", ".join(registry.get_project_names())
        return f"Error: Project '{project}' not found. Available: {available}"

    if entry.status != ProjectStatus.LOADED:
        not_ready = not_ready_response(registry, project)
        if not_ready:
            return not_ready

    if not entry.spec:
        return f"Error: Project '{project}' not loaded. Call refresh_spec to reload it."

    result = ListTagsResult(tags=entry.spec.tags)
    return result.model_dump_json(indent=2)
