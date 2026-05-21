"""Project registry - manages loaded OpenAPI specs in memory."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from openapi_mcp_server.indexer import EndpointIndex
from openapi_mcp_server.loader.local import LocalFileLoader
from openapi_mcp_server.loader.remote import RemoteHttpLoader
from openapi_mcp_server.models import (
    AppConfig,
    ProjectConfig,
    ProjectEntry,
    ProjectInfo,
    ProjectStatus,
)
from openapi_mcp_server.parser import ParseError, parse_spec

logger = logging.getLogger(__name__)


class ProjectRegistry:
    def __init__(self, config: AppConfig):
        self.config = config
        self._projects: dict[str, ProjectEntry] = {}
        self._indexes: dict[str, EndpointIndex] = {}
        self._loaders: dict[str, LocalFileLoader | RemoteHttpLoader] = {}

        for name, proj_config in config.projects.items():
            self._projects[name] = ProjectEntry(config=proj_config)
            self._loaders[name] = self._create_loader(proj_config)

    def _create_loader(self, config: ProjectConfig) -> LocalFileLoader | RemoteHttpLoader:
        if config.source == "local":
            return LocalFileLoader(config.path)
        return RemoteHttpLoader(
            url=config.url,
            timeout=config.request_timeout or self.config.settings.request_timeout,
            headers=config.headers,
        )

    async def load_all(self) -> None:
        for name in list(self._projects.keys()):
            await self.load_project(name)

    async def load_project(self, name: str) -> bool:
        entry = self._projects.get(name)
        if not entry:
            logger.warning(f"Unknown project: {name}")
            return False

        loader = self._loaders[name]
        entry.status = ProjectStatus.LOADING

        try:
            raw = await loader.load()
            spec = parse_spec(raw)
            entry.spec = spec
            entry.status = ProjectStatus.LOADED
            entry.last_updated = datetime.now(timezone.utc)
            entry.last_checked = datetime.now(timezone.utc)
            entry.error_message = None

            self._indexes[name] = EndpointIndex(spec.endpoints)
            logger.info(f"Loaded project '{name}': {len(spec.endpoints)} endpoints")
            return True

        except (ParseError, Exception) as e:
            entry.status = ProjectStatus.ERROR
            entry.error_message = str(e)
            logger.error(f"Failed to load project '{name}': {e}")
            return False

    async def check_and_refresh(self, name: str) -> bool:
        entry = self._projects.get(name)
        if not entry or entry.status == ProjectStatus.LOADING:
            return False

        loader = self._loaders.get(name)
        if not loader:
            return False

        try:
            changed = await loader.has_changed()
            entry.last_checked = datetime.now(timezone.utc)

            if changed:
                old_version = entry.spec.version if entry.spec else None
                result = await self.load_project(name)
                if result:
                    logger.info(f"Project '{name}' updated")
                return result
            return False

        except Exception as e:
            logger.error(f"Error checking project '{name}': {e}")
            return False

    def get_index(self, name: str) -> EndpointIndex | None:
        return self._indexes.get(name)

    def get_entry(self, name: str) -> ProjectEntry | None:
        return self._projects.get(name)

    def list_projects(self) -> list[ProjectInfo]:
        result = []
        for name, entry in self._projects.items():
            config = entry.config
            result.append(
                ProjectInfo(
                    name=name,
                    source=config.source,
                    location=config.path or config.url or "",
                    title=entry.spec.title if entry.spec else None,
                    version=entry.spec.version if entry.spec else None,
                    endpoint_count=len(entry.spec.endpoints) if entry.spec else 0,
                    last_updated=entry.last_updated.isoformat() if entry.last_updated else None,
                    status=entry.status.value,
                )
            )
        return result

    def get_project_names(self) -> list[str]:
        return list(self._projects.keys())

    def get_refresh_interval(self, name: str) -> int:
        entry = self._projects.get(name)
        if not entry:
            return self.config.settings.refresh_interval
        return entry.config.refresh_interval or self.config.settings.refresh_interval
