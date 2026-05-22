"""Remote HTTP loader."""

from __future__ import annotations

import hashlib
from typing import Any

import httpx

from openapi_mcp_server.loader.base import BaseLoader


class RemoteHttpLoader(BaseLoader):
    def __init__(
        self,
        url: str,
        timeout: int = 30,
        headers: dict[str, str] | None = None,
    ):
        self.url = url
        self.timeout = timeout
        self.headers = headers or {}
        self._last_etag: str | None = None
        self._last_hash: str | None = None

    async def load(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.url, headers=self.headers)
            response.raise_for_status()

            if etag := response.headers.get("etag"):
                self._last_etag = etag

            content = response.text
            self._last_hash = hashlib.sha256(content.encode()).hexdigest()

            content_type = response.headers.get("content-type", "")
            is_yaml = (
                "yaml" in content_type
                or self.url.endswith((".yaml", ".yml"))
            )

            if is_yaml:
                import yaml

                return yaml.safe_load(content)
            import json

            return json.loads(content)

    async def has_changed(self) -> bool:
        request_headers = dict(self.headers)
        if self._last_etag:
            request_headers["If-None-Match"] = self._last_etag

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.url, headers=request_headers)

                if response.status_code == 304:
                    return False

                response.raise_for_status()
                current_hash = hashlib.sha256(response.text.encode()).hexdigest()
                return current_hash != self._last_hash
        except httpx.HTTPError:
            return False
