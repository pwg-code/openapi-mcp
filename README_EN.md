English | [中文](README.md)

# OpenAPI MCP Server

> Let Claude Code and other AI coding assistants **understand your backend APIs instantly** — no more manually feeding docs, no more burning tokens exploring codebases.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-green)](https://modelcontextprotocol.io)
[![OpenAPI 3.x](https://img.shields.io/badge/OpenAPI-3.x-orange)](https://swagger.io/specification/)

**OpenAPI MCP Server** is a lightweight [MCP (Model Context Protocol)](https://modelcontextprotocol.io) service that turns your backend OpenAPI / Swagger specs into tools AI agents can call directly. One config, and your AI assistant can **search endpoints, inspect parameters, understand response schemas** — you never have to manually maintain API docs for AI again.

**Keywords**: `Claude Code` `MCP Server` `OpenAPI` `Swagger` `API Discovery` `AI Coding Assistant` `Cursor` `Windsurf` `Model Context Protocol`

---

## The Pain

I'm a full-stack developer working on frontend-backend separated projects. When building the frontend, AI coding assistants (Claude Code, Cursor, etc.) simply don't know what backend APIs exist — and that's where things always break down.

I've tried several approaches. None of them really work:

**Let AI explore the backend codebase?** Way too slow, and it burns tokens like crazy. AI has to read Controllers, Services, DTOs — a single endpoint definition is scattered across multiple files, and even after reading all of them, AI might still misunderstand. For a mid-size backend project, just "understanding the APIs" costs tens of thousands of tokens, not counting the rework from misinterpretation.

**Manually write API docs for AI?** It works, until the backend updates. Rename a field, add a parameter, tweak a response structure — the docs need to be updated too. When the backend iterates fast, docs are always behind the code. AI writing frontend code from outdated docs? That's bugs waiting to happen.

**Copy-paste Swagger UI content into every conversation?** Even worse. One endpoint's parameters, request body, and response schema pasted in is a massive blob of JSON. A few endpoints later, your context window is full.

**What I really want is simple**: an AI assistant that can **look up** what backend APIs exist and how to call them, and **automatically knows** when they change. I shouldn't be the human doc-mule between AI and the backend.

That's exactly what OpenAPI MCP Server does — **turns backend API specs into a native AI capability**.

---

## Quick Start

### Clone the project

```bash
git clone https://github.com/pwg-code/openapi-mcp.git
cd openapi-mcp
```

### Install dependencies

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv pip install -e .
```

Or using pip:

```bash
pip install -e .
```

---

## Claude Code Configuration

MCP Servers are launched automatically by the client — just declare them in your config.

### Project-level config

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "openapi": {
      "command": "<OPENAPI_MCP_PATH>",
      "args": [
        "serve",
        "--url", "user-service=https://api.example.com/v3/api-docs",
        "--url", "order-service=https://order.internal/api-docs",
        "--file", "petstore=./specs/petstore.json"
      ]
    }
  }
}
```

> Replace `<OPENAPI_MCP_PATH>` with the full path to the `openapi-mcp` executable, e.g. `D:/project/private/openapi-mcp/.venv/Scripts/openapi-mcp.exe`

### Global config

Add to `~/claude.json` to share across all projects:

```json
{
  "mcpServers": {
    "openapi": {
      "command": "<OPENAPI_MCP_PATH>",
      "args": [
        "serve",
        "--url", "suibian=http://localhost:8000/openapi.json",
        "--file", "petstore=./specs/petstore.json"
      ]
    }
  }
}
```

Once configured, Claude Code auto-starts the MCP Server. Just use natural language:

```
> What endpoints does the user service have?
> Search for login-related endpoints
> What are the request parameters for this endpoint?
> Write frontend code to call this endpoint
```

## OpenCode Configuration

Create `opencode.json` in your project root:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "openapi": {
      "type": "local",
      "enabled": true,
      "command": [
        "<OPENAPI_MCP_PATH>",
        "serve",
        "--url",
        "suibian=http://localhost:8000/openapi.json"
      ]
    }
  }
}
```

> Replace `<OPENAPI_MCP_PATH>` with the full path to the `openapi-mcp` executable, e.g. `D:/project/private/openapi-mcp/.venv/Scripts/openapi-mcp.exe`

AI automatically calls these tools to fetch API info — no manual action needed:

| Tool | Purpose |
|------|---------|
| `search_endpoints` | Search endpoints by keyword (matches path, summary, tag, operationId) |
| `get_endpoint_detail` | Get full endpoint details: parameters, request body, responses (`$ref` resolved inline) |
| `list_projects` | List all loaded projects with status |
| `list_tags` | Browse endpoint groups by functional module |
| `refresh_spec` | Manually trigger a refresh to reload API specs |

---

## Configuration Reference

### CLI arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--url NAME=URL` | string | — | Remote OpenAPI spec URL, can be repeated for multiple sources |
| `--file NAME=PATH` | string | — | Local OpenAPI spec file path, can be repeated for multiple sources |
| `--refresh-interval` | int | `300` | Auto-refresh interval in seconds, `0` to disable |
| `--request-timeout` | int | `30` | Remote request timeout in seconds |

### Refresh mechanism

| Source type | Change detection | Description |
|-------------|-----------------|-------------|
| Local file (`--file`) | SHA-256 hash comparison | Reads file and computes hash each check; skips if unchanged |
| Remote URL (`--url`) | ETag + If-None-Match conditional request | 304 response means no change; otherwise hash comparison |

- Refresh failures don't affect cached data — service stays available
- `--refresh-interval 0` disables auto-refresh; `refresh_spec` still works for manual triggers

---

## Requirements

- Python >= 3.10
- OpenAPI 3.x (3.0 / 3.1)

---

If you're tired of being the doc-mule between AI and your backend, drop a Star. Got ideas or issues? Open an Issue — let's make this better together.