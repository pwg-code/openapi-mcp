"""Tests for refresh manager: backoff retry scheduling and manual refresh."""

import asyncio

import pytest

from openapi_mcp_server.models import AppConfig, ProjectConfig, ProjectStatus, Settings
from openapi_mcp_server.refresh import RefreshManager, retry_delay
from openapi_mcp_server.registry import ProjectRegistry
from tests.conftest import FakeLoader


# --- Exponential backoff schedule: base, 2x, 4x, 8x, capped at 5 minutes ---


def test_retry_delay_schedule():
    assert retry_delay(15, 0) == 15
    assert retry_delay(15, 1) == 15
    assert retry_delay(15, 2) == 30
    assert retry_delay(15, 3) == 60
    assert retry_delay(15, 4) == 120
    assert retry_delay(15, 5) == 300
    assert retry_delay(15, 10) == 300


def test_retry_delay_uses_configured_base_interval():
    assert retry_delay(20, 1) == 20
    assert retry_delay(20, 2) == 40
    assert retry_delay(60, 6) == 300


# --- Backoff retry loop for failed projects ---


@pytest.mark.asyncio
async def test_failed_project_retried_until_success():
    """A failed project is retried automatically and becomes usable after recovery."""
    config = AppConfig(
        settings=Settings(refresh_interval=1, request_timeout=5),
        projects={"x": ProjectConfig(name="x", source="remote", url="http://x/spec.json")},
    )
    registry = ProjectRegistry(config)
    loader = FakeLoader(results=[ConnectionError("refused"), ConnectionError("refused"), 0.0])
    registry._loaders["x"] = loader

    # Initial load fails twice to enter the backoff state
    assert await registry.load_project("x") is False
    assert await registry.load_project("x") is False
    assert registry.get_entry("x").failure_count == 2

    manager = RefreshManager(registry)
    manager.start()
    try:
        for _ in range(80):  # up to ~8s
            await asyncio.sleep(0.1)
            if registry.get_entry("x").status == ProjectStatus.LOADED:
                break
        assert registry.get_entry("x").status == ProjectStatus.LOADED
        assert registry.get_entry("x").failure_count == 0
        assert loader.calls == 3
    finally:
        manager.stop()


@pytest.mark.asyncio
async def test_loaded_project_keeps_periodic_refresh():
    """Loaded projects keep the normal periodic refresh, unaffected by backoff logic."""
    config = AppConfig(
        settings=Settings(refresh_interval=1, request_timeout=5),
        projects={"x": ProjectConfig(name="x", source="remote", url="http://x/spec.json")},
    )
    registry = ProjectRegistry(config)
    loader = FakeLoader(results=[0.0])
    registry._loaders["x"] = loader
    await registry.load_all()
    assert loader.calls == 1

    manager = RefreshManager(registry)
    manager.start()
    try:
        await asyncio.sleep(2.2)
        assert registry.get_entry("x").status == ProjectStatus.LOADED
        # has_changed returns False so no reload happens; the loop must not error out
        assert loader.calls == 1
    finally:
        manager.stop()


# --- Manual refresh (refresh_spec) bypasses backoff and merges in-flight loads ---


@pytest.mark.asyncio
async def test_manual_refresh_recovers_failed_project_immediately():
    """refresh_spec on a failed project triggers an immediate load regardless of backoff."""
    config = AppConfig(
        settings=Settings(refresh_interval=15, request_timeout=5),
        projects={"x": ProjectConfig(name="x", source="remote", url="http://x/spec.json")},
    )
    registry = ProjectRegistry(config)
    loader = FakeLoader(results=[ConnectionError("refused"), 0.0])
    registry._loaders["x"] = loader

    assert await registry.load_project("x") is False
    assert registry.get_entry("x").failure_count == 1

    loader.results = [0.0]  # backend recovered
    manager = RefreshManager(registry)
    results = await manager.refresh_project("x")

    assert results[0]["updated"] is True
    assert registry.get_entry("x").status == ProjectStatus.LOADED
    assert registry.get_entry("x").failure_count == 0
    assert loader.calls == 2


@pytest.mark.asyncio
async def test_manual_refresh_merges_with_inflight_load():
    """refresh_spec during an in-flight load returns that load's result without a new request."""
    config = AppConfig(
        settings=Settings(refresh_interval=15, request_timeout=5),
        projects={"x": ProjectConfig(name="x", source="remote", url="http://x/spec.json")},
    )
    registry = ProjectRegistry(config)
    loader = FakeLoader(results=[0.1])
    registry._loaders["x"] = loader

    manager = RefreshManager(registry)
    background = asyncio.create_task(registry.load_project("x"))
    await asyncio.sleep(0.02)  # let the background load start

    results = await manager.refresh_project("x")
    assert results[0]["updated"] is True
    assert await background is True
    assert loader.calls == 1


@pytest.mark.asyncio
async def test_manual_refresh_reports_error_for_unknown_project():
    config = AppConfig(
        settings=Settings(refresh_interval=15, request_timeout=5),
        projects={"x": ProjectConfig(name="x", source="remote", url="http://x/spec.json")},
    )
    registry = ProjectRegistry(config)
    manager = RefreshManager(registry)

    results = await manager.refresh_project("ghost")
    assert results[0]["updated"] is False
    assert results[0]["error"] == "Unknown project"
