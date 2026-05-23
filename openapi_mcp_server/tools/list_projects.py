"""list_projects tool."""

from __future__ import annotations

from openapi_mcp_server.models import ListProjectsResult
from openapi_mcp_server.registry import ProjectRegistry


async def handle(registry: ProjectRegistry, arguments: dict) -> str:
    projects = registry.list_projects()
    result = ListProjectsResult(projects=projects)
    return result.model_dump_json(indent=2)
