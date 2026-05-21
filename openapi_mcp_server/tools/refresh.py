"""refresh_spec tool."""

from __future__ import annotations

from openapi_mcp_server.models import ProjectRefreshResult, RefreshResult
from openapi_mcp_server.registry import ProjectRegistry
from openapi_mcp_server.refresh import RefreshManager


TOOL_NAME = "refresh_spec"
TOOL_DESCRIPTION = """Reload OpenAPI spec(s) from source. Call when the API may have changed — e.g. "the endpoint is missing", "API was updated", "refresh the spec", or search_endpoints returns unexpected results."""

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project name to refresh. Omit to refresh all projects.",
        },
    },
}


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
