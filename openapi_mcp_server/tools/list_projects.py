"""list_projects tool."""

from __future__ import annotations

from openapi_mcp_server.models import ListProjectsResult
from openapi_mcp_server.registry import ProjectRegistry


TOOL_NAME = "list_projects"
TOOL_DESCRIPTION = """List all loaded OpenAPI projects with name, version, and endpoint count. Call this first when you don't know the project name — e.g. "what APIs are available", "show me the projects", "which services do we have". You need the project name to call any other tool."""

INPUT_SCHEMA = {
    "type": "object",
    "properties": {},
}


async def handle(registry: ProjectRegistry, arguments: dict) -> str:
    projects = registry.list_projects()
    result = ListProjectsResult(projects=projects)
    return result.model_dump_json(indent=2)
