"""Tests for source loaders."""

import json
import pytest

from openapi_mcp_server.loader.local import LocalFileLoader


@pytest.mark.asyncio
async def test_local_loader_json(tmp_path):
    spec_file = tmp_path / "api.json"
    spec_data = {"openapi": "3.0.0", "info": {"title": "Test", "version": "1.0"}}
    spec_file.write_text(json.dumps(spec_data), encoding="utf-8")

    loader = LocalFileLoader(str(spec_file))
    result = await loader.load()
    assert result["openapi"] == "3.0.0"
    assert result["info"]["title"] == "Test"


@pytest.mark.asyncio
async def test_local_loader_yaml(tmp_path):
    import yaml
    spec_file = tmp_path / "api.yaml"
    spec_data = {"openapi": "3.0.0", "info": {"title": "Test YAML", "version": "1.0"}}
    spec_file.write_text(yaml.dump(spec_data), encoding="utf-8")

    loader = LocalFileLoader(str(spec_file))
    result = await loader.load()
    assert result["info"]["title"] == "Test YAML"


@pytest.mark.asyncio
async def test_local_has_changed(tmp_path):
    spec_file = tmp_path / "api.json"
    spec_file.write_text(json.dumps({"openapi": "3.0.0"}), encoding="utf-8")

    loader = LocalFileLoader(str(spec_file))
    await loader.load()

    assert not await loader.has_changed()

    spec_file.write_text(json.dumps({"openapi": "3.0.1", "info": {"title": "changed"}}), encoding="utf-8")
    assert await loader.has_changed()