import time
from typing import Any

class InMemoryCache:
    def __init__(self): self._values = {}
    def set(self, key: str, value: Any, ttl: float = 300): self._values[key] = (time.monotonic() + ttl, value)
    def get(self, key: str, default=None):
        item = self._values.get(key)
        if not item: return default
        if item[0] <= time.monotonic(): self._values.pop(key, None); return default
        return item[1]
    def delete(self, key: str): self._values.pop(key, None)
cache = InMemoryCache()
