"""Tests for project registry."""

import asyncio

import pytest

from openapi_mcp_server.models import AppConfig, ProjectConfig, Settings, ProjectStatus
from openapi_mcp_server.registry import ProjectRegistry
from tests.conftest import FakeLoader


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


# --- Background/concurrent loading ---


@pytest.mark.asyncio
async def test_load_all_concurrent_slow_project_does_not_block_others():
    """A hung project must not delay other projects' readiness."""
    config = AppConfig(
        settings=Settings(),
        projects={
            "slow": ProjectConfig(name="slow", source="remote", url="http://slow/spec.json"),
            "fast": ProjectConfig(name="fast", source="remote", url="http://fast/spec.json"),
        },
    )
    registry = ProjectRegistry(config)
    registry._loaders["slow"] = FakeLoader(results=[30.0])  # hangs far beyond the test
    registry._loaders["fast"] = FakeLoader(results=[0.0])

    load_task = asyncio.create_task(registry.load_all())
    await asyncio.sleep(0.05)

    assert registry.get_entry("fast").status == ProjectStatus.LOADED
    assert registry.get_entry("slow").status == ProjectStatus.LOADING

    load_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await load_task


@pytest.mark.asyncio
async def test_load_all_waits_for_all_projects():
    config = AppConfig(
        settings=Settings(),
        projects={
            "a": ProjectConfig(name="a", source="remote", url="http://a/spec.json"),
            "b": ProjectConfig(name="b", source="remote", url="http://b/spec.json"),
        },
    )
    registry = ProjectRegistry(config)
    registry._loaders["a"] = FakeLoader(results=[0.0])
    registry._loaders["b"] = FakeLoader(results=[0.05])

    await asyncio.wait_for(registry.load_all(), timeout=5)

    assert registry.get_entry("a").status == ProjectStatus.LOADED
    assert registry.get_entry("b").status == ProjectStatus.LOADED


# --- In-flight load merging ---


@pytest.mark.asyncio
async def test_concurrent_load_project_merged_into_single_load():
    """Two concurrent load_project calls trigger exactly one loader.load."""
    config = AppConfig(
        projects={"x": ProjectConfig(name="x", source="remote", url="http://x/spec.json")},
    )
    registry = ProjectRegistry(config)
    loader = FakeLoader(results=[0.1])
    registry._loaders["x"] = loader

    results = await asyncio.gather(
        registry.load_project("x"),
        registry.load_project("x"),
    )

    assert results == [True, True]
    assert loader.calls == 1


# --- Failure counting / backoff state ---


@pytest.mark.asyncio
async def test_failure_count_increments_then_resets_on_success():
    config = AppConfig(
        projects={"x": ProjectConfig(name="x", source="remote", url="http://x/spec.json")},
    )
    registry = ProjectRegistry(config)
    loader = FakeLoader(results=[ConnectionError("refused"), ConnectionError("refused"), 0.0])
    registry._loaders["x"] = loader

    assert await registry.load_project("x") is False
    entry = registry.get_entry("x")
    assert entry.status == ProjectStatus.ERROR
    assert entry.failure_count == 1
    assert "refused" in entry.error_message

    assert await registry.load_project("x") is False
    assert registry.get_entry("x").failure_count == 2

    assert await registry.load_project("x") is True
    entry = registry.get_entry("x")
    assert entry.status == ProjectStatus.LOADED
    assert entry.failure_count == 0
    assert entry.error_message is None


@pytest.mark.asyncio
async def test_list_projects_exposes_error_message():
    config = AppConfig(
        projects={
            "bad": ProjectConfig(name="bad", source="local", path="/nonexistent/file.json"),
            "good": ProjectConfig(name="good", source="local", path="/nonexistent/good.json"),
        },
    )
    registry = ProjectRegistry(config)
    registry._loaders["good"] = FakeLoader(results=[0.0])
    await registry.load_all()

    infos = {p.name: p for p in registry.list_projects()}
    assert infos["bad"].status == "error"
    assert infos["bad"].error_message is not None
    assert infos["good"].status == "loaded"
    assert infos["good"].error_message is None