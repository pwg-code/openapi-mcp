"""Base loader interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLoader(ABC):
    @abstractmethod
    async def load(self) -> dict[str, Any]:
        """Load and return raw OpenAPI spec as dict."""

    @abstractmethod
    async def has_changed(self) -> bool:
        """Check if the source has changed since last load."""
