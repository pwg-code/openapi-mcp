"""get_endpoint_detail tool."""

from __future__ import annotations

from openapi_mcp_server.registry import ProjectRegistry


TOOL_NAME = "get_endpoint_detail"
TOOL_DESCRIPTION = """Get full details of an API endpoint: parameters, request body schema, and response schemas. Always call this after search_endpoints — the search only returns summaries. You need this to know required/optional parameters, request body fields, and response formats before calling an API. All $ref references are resolved inline."""

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project name (use list_projects to discover available names)",
        },
        "path": {
            "type": "string",
            "description": "Endpoint path from search results (e.g. /api/v1/users/{id})",
        },
        "method": {
            "type": "string",
            "description": "HTTP method from search results: GET, POST, PUT, DELETE, PATCH",
        },
    },
    "required": ["project", "path", "method"],
}


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

    return endpoint.model_dump_json(indent=2)
