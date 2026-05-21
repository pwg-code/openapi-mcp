"""Shared test fixtures."""

import json
from pathlib import Path

import pytest

from openapi_mcp_server.config import build_config
from openapi_mcp_server.models import AppConfig, ProjectConfig, Settings
from openapi_mcp_server.registry import ProjectRegistry

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PETSTORE_SPEC = FIXTURES_DIR / "petstore.json"


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
