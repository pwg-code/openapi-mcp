"""Shared test fixtures."""

import asyncio
import json
from pathlib import Path

import pytest

from openapi_mcp_server.config import build_config
from openapi_mcp_server.models import AppConfig, ProjectConfig, Settings
from openapi_mcp_server.registry import ProjectRegistry

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PETSTORE_SPEC = FIXTURES_DIR / "petstore.json"

MINIMAL_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Fake API", "version": "1.0.0"},
    "paths": {},
}


class FakeLoader:
    """Scriptable loader: per-call delays, failures, then success."""

    def __init__(self, results=None):
        # results: list of either float (delay before success) or Exception (fail after delay)
        self.results = list(results) if results else [0.0]
        self.calls = 0
        self.delays = []

    async def load(self):
        self.calls += 1
        idx = min(self.calls, len(self.results)) - 1
        outcome = self.results[idx]
        delay, error = (outcome, None) if isinstance(outcome, (int, float)) else (0.0, outcome)
        if delay:
            self.delays.append(delay)
            await asyncio.sleep(delay)
        else:
            self.delays.append(0.0)
        if error is not None:
            raise error
        return json.loads(json.dumps(MINIMAL_SPEC))

    async def has_changed(self):
        return False


@pytest.fixture
def petstore_raw():
    return json.loads(PETSTORE_SPEC.read_text(encoding="utf-8"))


@pytest.fixture
def petstore_config(tmp_path):
    spec_path = tmp_path / "petstore.json"
    spec_path.write_text(PETSTORE_SPEC.read_text(encoding="utf-8"), encoding="utf-8")

    config = AppConfig(
        settings=Settings(),
        projects={
            "petstore": ProjectConfig(
                name="petstore",
                source="local",
                path=str(spec_path),
            ),
        },
    )
    return config, str(spec_path)


@pytest.fixture
async def petstore_registry(petstore_config):
    config, _ = petstore_config
    registry = ProjectRegistry(config)
    await registry.load_all()
    return registry
