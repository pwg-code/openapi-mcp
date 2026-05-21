"""search_endpoints tool."""

from __future__ import annotations

from openapi_mcp_server.registry import ProjectRegistry


TOOL_NAME = "search_endpoints"
TOOL_DESCRIPTION = """Find API endpoints by keyword. Use this whenever the user asks about any API, endpoint, or REST operation — e.g. "is there an API for X", "find the login endpoint", "what APIs exist for users", "how to call X". Searches paths, summaries, tags, and operationIds. Returns basic info; use get_endpoint_detail for full details."""

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project name (use list_projects to discover available names)",
        },
        "query": {
            "type": "string",
            "description": "Search keyword — matches path, summary, tag, operationId (e.g. 'user', 'login', 'order')",
        },
        "method": {
            "type": "string",
            "description": "Filter by HTTP method: GET, POST, PUT, DELETE, PATCH",
        },
        "tag": {
            "type": "string",
            "description": "Filter by tag name (use list_tags to discover available tags)",
        },
        "limit": {
            "type": "integer",
            "description": "Max results to return (default: 10)",
            "default": 10,
        },
    },
    "required": ["project", "query"],
}


async def handle(registry: ProjectRegistry, arguments: dict) -> str:
    project = arguments.get("project", "")
    query = arguments.get("query", "")
    method = arguments.get("method")
    tag = arguments.get("tag")
    limit = arguments.get("limit", 10)

    index = registry.get_index(project)
    if index is None:
        available = ", ".join(registry.get_project_names())
        return f"Error: Project '{project}' not found. Available: {available}"

    result = index.search(query=query, method=method, tag=tag, limit=limit)
    return result.model_dump_json(indent=2)
