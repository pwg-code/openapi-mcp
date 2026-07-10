"""Configuration building from CLI arguments."""

from __future__ import annotations

from openapi_mcp_server.models import AppConfig, ProjectConfig, Settings


def _parse_name_value(pair: str, flag: str) -> tuple[str, str]:
    """Parse NAME=VALUE from a CLI argument like --url name=url or --file name=path."""
    if "=" not in pair:
        raise ValueError(f"Invalid format for {flag}: '{pair}'. Expected NAME=VALUE (e.g. local-api=http://localhost:8000/openapi.json)")
    name, value = pair.split("=", 1)
    if not name or not value:
        raise ValueError(f"Invalid format for {flag}: '{pair}'. Both NAME and VALUE must be non-empty.")
    return name.strip(), value.strip()


def build_config(
    urls: list[str] | None = None,
    files: list[str] | None = None,
    refresh_interval: int = 15,
    request_timeout: int = 30,
) -> AppConfig:
    """Build AppConfig from CLI arguments."""
    projects: dict[str, ProjectConfig] = {}

    for pair in (urls or []):
        name, url = _parse_name_value(pair, "--url")
        projects[name] = ProjectConfig(name=name, source="remote", url=url)

    for pair in (files or []):
        name, path = _parse_name_value(pair, "--file")
        projects[name] = ProjectConfig(name=name, source="local", path=path)

    if not projects:
        raise ValueError("At least one --url or --file is required")

    return AppConfig(
        settings=Settings(refresh_interval=refresh_interval, request_timeout=request_timeout),
        projects=projects,
    )
