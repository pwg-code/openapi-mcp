"""Remote HTTP loader."""

from __future__ import annotations

import asyncio
import hashlib
import ssl
import threading
from typing import Any

import certifi
import httpx

from openapi_mcp_server.loader.base import BaseLoader

_ssl_context: ssl.SSLContext | None = None
_ssl_context_lock = threading.Lock()


def _get_ssl_context() -> ssl.SSLContext:
    """Build the TLS context once per process; loading the CA bundle is expensive."""
    global _ssl_context
    if _ssl_context is None:
        with _ssl_context_lock:
            if _ssl_context is None:
                _ssl_context = ssl.create_default_context(cafile=certifi.where())
    return _ssl_context


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
        self._client: httpx.AsyncClient | None = None
        self._client_lock: asyncio.Lock | None = None

    def _build_client(self) -> httpx.AsyncClient:
        # Runs in a worker thread: client construction loads the CA bundle and
        # can take seconds on Windows, which would otherwise stall the event loop.
        return httpx.AsyncClient(
            timeout=self.timeout,
            trust_env=False,
            verify=_get_ssl_context(),
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            if self._client_lock is None:
                self._client_lock = asyncio.Lock()
            async with self._client_lock:
                if self._client is None:
                    self._client = await asyncio.to_thread(self._build_client)
        return self._client

    async def load(self) -> dict[str, Any]:
        client = await self._get_client()
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
            client = await self._get_client()
            response = await client.get(self.url, headers=request_headers)

            if response.status_code == 304:
                return False

            response.raise_for_status()
            current_hash = hashlib.sha256(response.text.encode()).hexdigest()
            return current_hash != self._last_hash
        except httpx.HTTPError:
            return False
