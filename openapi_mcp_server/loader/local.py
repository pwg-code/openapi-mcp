"""Local file loader."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from openapi_mcp_server.loader.base import BaseLoader


class LocalFileLoader(BaseLoader):
    def __init__(self, path: str):
        self.path = Path(path).resolve()
        self._last_mtime: float | None = None
        self._last_hash: str | None = None

    async def load(self) -> dict[str, Any]:
        content = self.path.read_text(encoding="utf-8")
        self._last_mtime = self.path.stat().st_mtime
        self._last_hash = hashlib.sha256(content.encode()).hexdigest()

        if self.path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(content)
        return json.loads(content)

    async def has_changed(self) -> bool:
        if not self.path.exists():
            return False
        try:
            content = self.path.read_text(encoding="utf-8")
        except OSError:
            return False
        current_hash = hashlib.sha256(content.encode()).hexdigest()
        return current_hash != self._last_hash
