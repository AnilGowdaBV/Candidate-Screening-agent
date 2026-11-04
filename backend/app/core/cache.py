"""Short-lived memory cache so repeat dashboard reads skip the database."""

import time
from threading import Lock
from typing import Any, Optional

_lock = Lock()
_values: dict[Any, tuple[float, Any]] = {}
TTL_SECONDS = 60


def cache_get(key: Any) -> Optional[Any]:
    now = time.time()
    with _lock:
        item = _values.get(key)
        if item is None:
            return None
        saved_at, value = item
        if now - saved_at > TTL_SECONDS:
            _values.pop(key, None)
            return None
        return value


def cache_put(key: Any, value: Any) -> None:
    with _lock:
        _values[key] = (time.time(), value)


def cache_invalidate_prefix(*prefix: Any) -> None:
    with _lock:
        stale = [key for key in _values if isinstance(key, tuple) and key[: len(prefix)] == prefix]
        for key in stale:
            _values.pop(key, None)
