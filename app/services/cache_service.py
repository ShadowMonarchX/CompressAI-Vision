"""Small in-memory TTL cache with a swappable backend-friendly interface."""

import threading
import time
from typing import Any


class InMemoryCache:
    """Thread-safe process-local cache for short-lived values."""

    def __init__(self) -> None:
        self._values: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, ttl: float = 300) -> None:
        """Store a value until ``ttl`` seconds after this call."""
        if not key:
            raise ValueError("cache key must not be empty")
        if ttl <= 0:
            raise ValueError("ttl must be greater than zero")
        with self._lock:
            self._values[key] = (time.monotonic() + ttl, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a live value, removing expired entries on access."""
        with self._lock:
            item = self._values.get(key)
            if item is None:
                return default
            if item[0] <= time.monotonic():
                self._values.pop(key, None)
                return default
            return item[1]

    def delete(self, key: str) -> None:
        """Remove a key if present."""
        with self._lock:
            self._values.pop(key, None)


cache = InMemoryCache()
