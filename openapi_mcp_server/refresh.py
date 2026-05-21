"""Refresh manager - periodic and on-demand spec refresh."""

from __future__ import annotations

import asyncio
import logging
import time

from openapi_mcp_server.registry import ProjectRegistry

logger = logging.getLogger(__name__)


class RefreshManager:
    def __init__(self, registry: ProjectRegistry):
        self.registry = registry
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False

    def start(self) -> None:
        self._running = True
        for name in self.registry.get_project_names():
            interval = self.registry.get_refresh_interval(name)
            if interval > 0:
                self._tasks[name] = asyncio.create_task(self._refresh_loop(name, interval))
        logger.info(f"Refresh manager started for {len(self._tasks)} projects")

    def stop(self) -> None:
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        logger.info("Refresh manager stopped")

    async def _refresh_loop(self, name: str, interval: int) -> None:
        while self._running:
            try:
                await asyncio.sleep(interval)
                if not self._running:
                    break
                await self.registry.check_and_refresh(name)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Refresh loop error for '{name}': {e}")
                await asyncio.sleep(60)

    async def refresh_project(self, name: str | None = None) -> list[dict]:
        results = []
        names = [name] if name else self.registry.get_project_names()

        for n in names:
            entry = self.registry.get_entry(n)
            if not entry:
                results.append({"project": n, "updated": False, "error": "Unknown project"})
                continue

            old_version = entry.spec.version if entry.spec else None
            success = await self.registry.load_project(n)

            if success:
                new_entry = self.registry.get_entry(n)
                new_version = new_entry.spec.version if new_entry and new_entry.spec else None
                results.append({
                    "project": n,
                    "updated": True,
                    "previous_version": old_version,
                    "current_version": new_version,
                })
            else:
                results.append({
                    "project": n,
                    "updated": False,
                    "error": entry.error_message or "Load failed",
                })

        return results
