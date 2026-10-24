"""In-process rate limits for paid calls. Per API process; move to Redis/Postgres when running several."""

import time
from collections import defaultdict, deque


class SlidingWindowLimit:
    def __init__(self, max_calls: int, window_seconds: float):
        self.max_calls, self.window = max_calls, window_seconds
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        calls = self._calls[key]
        while calls and now - calls[0] > self.window:
            calls.popleft()
        if len(calls) >= self.max_calls:
            return False
        calls.append(now)
        return True
