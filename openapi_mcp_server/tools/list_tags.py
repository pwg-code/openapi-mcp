"""list_tags tool."""

from __future__ import annotations

from openapi_mcp_server.models import ListTagsResult
from openapi_mcp_server.registry import ProjectRegistry


async def handle(registry: ProjectRegistry, arguments: dict) -> str:
    project = arguments.get("project", "")

    entry = registry.get_entry(project)
    if not entry or not entry.spec:
        available = ", ".join(registry.get_project_names())
        return f"Error: Project '{project}' not found or not loaded. Available: {available}"

    result = ListTagsResult(tags=entry.spec.tags)
    return result.model_dump_json(indent=2)
