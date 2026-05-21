"""list_tags tool."""

from __future__ import annotations

from openapi_mcp_server.models import ListTagsResult
from openapi_mcp_server.registry import ProjectRegistry


TOOL_NAME = "list_tags"
TOOL_DESCRIPTION = """List API tags (groups like 'Users', 'Orders', 'Auth') with endpoint counts. Use when the user wants to browse APIs by category — e.g. "what groups of APIs exist", "show me user-related endpoints", "what categories are there". Use tag names to filter search_endpoints."""

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project name (use list_projects to discover available names)",
        },
    },
    "required": ["project"],
}


async def handle(registry: ProjectRegistry, arguments: dict) -> str:
    project = arguments.get("project", "")

    entry = registry.get_entry(project)
    if not entry or not entry.spec:
        available = ", ".join(registry.get_project_names())
        return f"Error: Project '{project}' not found or not loaded. Available: {available}"

    result = ListTagsResult(tags=entry.spec.tags)
    return result.model_dump_json(indent=2)
