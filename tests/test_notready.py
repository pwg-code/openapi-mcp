"""Tests for tool responses when a project is loading or failed."""

import json
import time

import pytest

from openapi_mcp_server.models import AppConfig, ProjectConfig, ProjectStatus, Settings
from openapi_mcp_server.registry import ProjectRegistry
from openapi_mcp_server.tools import detail, list_projects, list_tags, search


def _loading_registry() -> ProjectRegistry:
    config = AppConfig(
        settings=Settings(),
        projects={"x": ProjectConfig(name="x", source="remote", url="http://x/spec.json")},
    )
    return ProjectRegistry(config)


async def _error_registry() -> ProjectRegistry:
    config = AppConfig(
        settings=Settings(),
        projects={"x": ProjectConfig(name="x", source="local", path="/nonexistent/file.json")},
    )
    registry = ProjectRegistry(config)
    await registry.load_all()
    return registry


# --- loading state: tools reply immediately with a structured status ---


@pytest.mark.asyncio
async def test_search_returns_loading_status():
    registry = _loading_registry()

    start = time.monotonic()
    result = await search.handle(registry, {"project": "x", "query": "user"})
    elapsed = time.monotonic() - start

    data = json.loads(result)
    assert data["status"] == "loading"
    assert "加载" in data["message"]
    assert "refresh_spec" in data["suggestion"]
    assert elapsed < 1.0  # must not block on the spec being unavailable


@pytest.mark.asyncio
async def test_detail_returns_loading_status():
    registry = _loading_registry()
    result = await detail.handle(registry, {"project": "x", "path": "/a", "method": "get"})
    data = json.loads(result)
    assert data["status"] == "loading"
    assert "refresh_spec" in data["suggestion"]


@pytest.mark.asyncio
async def test_list_tags_returns_loading_status():
    registry = _loading_registry()
    result = await list_tags.handle(registry, {"project": "x"})
    data = json.loads(result)
    assert data["status"] == "loading"
    assert "refresh_spec" in data["suggestion"]


# --- error state: tools reply immediately with the failure reason ---


@pytest.mark.asyncio
async def test_search_returns_error_status_with_reason():
    registry = await _error_registry()
    result = await search.handle(registry, {"project": "x", "query": "user"})

    data = json.loads(result)
    assert data["status"] == "error"
    assert data["message"] is not None and data["message"] != ""
    assert "refresh_spec" in data["suggestion"]


@pytest.mark.asyncio
async def test_detail_returns_error_status_with_reason():
    registry = await _error_registry()
    result = await detail.handle(registry, {"project": "x", "path": "/a", "method": "get"})
    data = json.loads(result)
    assert data["status"] == "error"
    assert data["message"] is not None


@pytest.mark.asyncio
async def test_list_tags_returns_error_status_with_reason():
    registry = await _error_registry()
    result = await list_tags.handle(registry, {"project": "x"})
    data = json.loads(result)
    assert data["status"] == "error"
    assert data["message"] is not None


# --- ready project still works; unknown project keeps the old error ---


@pytest.mark.asyncio
async def test_ready_project_serves_search_normally(petstore_config):
    config, _ = petstore_config
    registry = ProjectRegistry(config)
    await registry.load_all()

    result = await search.handle(registry, {"project": "petstore", "query": "pet"})
    data = json.loads(result)
    assert "status" not in data
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_unknown_project_returns_not_found():
    registry = _loading_registry()
    result = await search.handle(registry, {"project": "ghost", "query": "user"})
    assert "not found" in result
    assert "Available" in result


# --- list_projects exposes per-project status and failure reason ---


@pytest.mark.asyncio
async def test_list_projects_shows_loading_and_error_states():
    loading = _loading_registry()
    failed = await _error_registry()

    out_loading = json.loads(await list_projects.handle(loading, {}))
    assert out_loading["projects"][0]["status"] == ProjectStatus.LOADING.value

    out_failed = json.loads(await list_projects.handle(failed, {}))
    proj = out_failed["projects"][0]
    assert proj["status"] == ProjectStatus.ERROR.value
    assert proj["error_message"] is not None
