"""Tests for project registry."""

import pytest

from openapi_mcp_server.models import AppConfig, ProjectConfig, Settings, ProjectStatus
from openapi_mcp_server.registry import ProjectRegistry


@pytest.mark.asyncio
async def test_load_all(petstore_registry):
    entry = petstore_registry.get_entry("petstore")
    assert entry is not None
    assert entry.status == ProjectStatus.LOADED
    assert entry.spec is not None
    assert entry.spec.title == "Petstore API"


@pytest.mark.asyncio
async def test_list_projects(petstore_registry):
    projects = petstore_registry.list_projects()
    assert len(projects) == 1
    assert projects[0].name == "petstore"
    assert projects[0].status == "loaded"
    assert projects[0].endpoint_count == 6


@pytest.mark.asyncio
async def test_get_index(petstore_registry):
    index = petstore_registry.get_index("petstore")
    assert index is not None
    result = index.search(query="pet")
    assert result.total >= 3


@pytest.mark.asyncio
async def test_unknown_project(petstore_registry):
    assert petstore_registry.get_entry("unknown") is None
    assert petstore_registry.get_index("unknown") is None


@pytest.mark.asyncio
async def test_load_nonexistent_project():
    config = AppConfig(
        projects={
            "missing": ProjectConfig(name="missing", source="local", path="/nonexistent/file.json"),
        },
    )
    registry = ProjectRegistry(config)
    await registry.load_all()

    entry = registry.get_entry("missing")
    assert entry is not None
    assert entry.status == ProjectStatus.ERROR
    assert entry.error_message is not None