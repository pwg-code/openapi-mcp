"""refresh_spec tool."""

from __future__ import annotations

from openapi_mcp_server.models import ProjectRefreshResult, RefreshResult
from openapi_mcp_server.registry import ProjectRegistry
from openapi_mcp_server.refresh import RefreshManager


async def handle(registry: ProjectRegistry, refresh_manager: RefreshManager, arguments: dict) -> str:
    project = arguments.get("project")
    results = await refresh_manager.refresh_project(project)

    refresh_results = [
        ProjectRefreshResult(
            project=r["project"],
            updated=r.get("updated", False),
            previous_version=r.get("previous_version"),
            current_version=r.get("current_version"),
            error=r.get("error"),
        )
        for r in results
    ]

    result = RefreshResult(results=refresh_results)
    return result.model_dump_json(indent=2)
