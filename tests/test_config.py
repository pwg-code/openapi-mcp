"""Tests for config building from CLI arguments."""

import pytest

from openapi_mcp_server.config import build_config, _parse_name_value


def test_build_config_with_url():
    config = build_config(urls=["local-api=http://localhost:8000/openapi.json"])
    assert "local-api" in config.projects
    assert config.projects["local-api"].source == "remote"
    assert config.projects["local-api"].url == "http://localhost:8000/openapi.json"


def test_build_config_with_file():
    config = build_config(files=["petstore=./petstore.json"])
    assert "petstore" in config.projects
    assert config.projects["petstore"].source == "local"
    assert config.projects["petstore"].path == "./petstore.json"


def test_build_config_with_both():
    config = build_config(
        urls=["api1=http://example.com/openapi.json"],
        files=["api2=./spec.json"],
    )
    assert len(config.projects) == 2
    assert config.projects["api1"].source == "remote"
    assert config.projects["api2"].source == "local"


def test_build_config_custom_settings():
    config = build_config(
        urls=["api=http://example.com/openapi.json"],
        refresh_interval=120,
        request_timeout=60,
    )
    assert config.settings.refresh_interval == 120
    assert config.settings.request_timeout == 60


def test_build_config_default_settings():
    config = build_config(urls=["api=http://example.com/openapi.json"])
    assert config.settings.refresh_interval == 15
    assert config.settings.request_timeout == 30


def test_build_config_no_projects():
    with pytest.raises(ValueError, match="At least one"):
        build_config()


def test_parse_name_value_valid():
    name, value = _parse_name_value("local-api=http://localhost:8000/openapi.json", "--url")
    assert name == "local-api"
    assert value == "http://localhost:8000/openapi.json"


def test_parse_name_value_with_equals_in_value():
    name, value = _parse_name_value("api=http://example.com?foo=bar", "--url")
    assert name == "api"
    assert value == "http://example.com?foo=bar"


def test_parse_name_value_no_equals():
    with pytest.raises(ValueError, match="Invalid format"):
        _parse_name_value("noequals", "--url")


def test_parse_name_value_empty_name():
    with pytest.raises(ValueError, match="non-empty"):
        _parse_name_value("=http://example.com", "--url")


def test_multiple_urls():
    config = build_config(urls=[
        "api1=http://localhost:8000/openapi.json",
        "api2=http://localhost:9000/openapi.json",
    ])
    assert len(config.projects) == 2
    assert "api1" in config.projects
    assert "api2" in config.projects