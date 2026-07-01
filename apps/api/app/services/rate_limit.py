from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass
class _Window:
    reset_at: float
    count: int


class InMemoryRateLimiter:
    def __init__(self, max_identifiers: int = 10_000) -> None:
        self._lock = Lock()
        self._windows: dict[str, _Window] = {}
        self._max_identifiers = max_identifiers

    def allow(self, identifier: str, limit: int, window_seconds: int) -> bool:
        if limit < 1:
            return False

        now = monotonic()
        window_seconds = max(1, window_seconds)
        key = identifier or "anonymous"

        with self._lock:
            self._prune_expired(now)
            window = self._windows.get(key)
            if window is None or now >= window.reset_at:
                self._make_room_for_identifier()
                self._windows[key] = _Window(reset_at=now + window_seconds, count=1)
                return True

            if window.count >= limit:
                return False

            window.count += 1
            return True

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()

    def _prune_expired(self, now: float) -> None:
        expired_keys = [key for key, window in self._windows.items() if now >= window.reset_at]
        for key in expired_keys:
            del self._windows[key]

    def _make_room_for_identifier(self) -> None:
        if len(self._windows) < self._max_identifiers:
            return

        oldest_key = min(self._windows, key=lambda key: self._windows[key].reset_at)
        del self._windows[oldest_key]


_limiter = InMemoryRateLimiter()


def check_rate_limit(identifier: str, limit: int, window_seconds: int = 60) -> bool:
    return _limiter.allow(identifier=identifier, limit=limit, window_seconds=window_seconds)


def reset_rate_limits() -> None:
    _limiter.reset()
