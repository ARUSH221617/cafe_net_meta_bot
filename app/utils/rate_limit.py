import time
from collections import defaultdict


class InMemoryRateLimiter:
    def __init__(self, max_events: int, window_seconds: int) -> None:
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        events = [event for event in self._events[key] if event >= cutoff]
        self._events[key] = events
        if len(events) >= self.max_events:
            return False
        events.append(now)
        return True
