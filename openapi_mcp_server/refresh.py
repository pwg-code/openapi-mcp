"""Refresh manager - periodic refresh, exponential backoff retry, and on-demand refresh."""

from __future__ import annotations

import asyncio
import logging

from openapi_mcp_server.models import ProjectStatus
from openapi_mcp_server.registry import ProjectRegistry

logger = logging.getLogger(__name__)

BACKOFF_CAP_SECONDS = 300
_RETRY_MULTIPLIERS = (1, 2, 4, 8)


def retry_delay(base_interval: int, failure_count: int) -> int:
    """Next retry delay after `failure_count` consecutive failures: base, 2x, 4x, 8x, capped."""
    if failure_count <= 1:
        return base_interval
    if failure_count - 1 >= len(_RETRY_MULTIPLIERS):
        return BACKOFF_CAP_SECONDS
    return min(base_interval * _RETRY_MULTIPLIERS[failure_count - 1], BACKOFF_CAP_SECONDS)


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
                entry = self.registry.get_entry(name)
                if entry and entry.status == ProjectStatus.ERROR:
                    delay = retry_delay(interval, entry.failure_count)
                else:
                    delay = interval
                await asyncio.sleep(delay)
                if not self._running:
                    break

                entry = self.registry.get_entry(name)
                if not entry:
                    continue
                if entry.status == ProjectStatus.ERROR:
                    logger.info(f"Retrying failed project '{name}' (failure #{entry.failure_count})")
                    await self.registry.load_project(name)
                elif entry.status == ProjectStatus.LOADED:
                    await self.registry.check_and_refresh(name)
                # LOADING: a load is already in flight; skip this round
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
