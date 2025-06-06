"""
Shared utilities
================

A single place for:

* global TokenBucket rate-limiter (requests-per-minute)
* retry_on_rate_limit decorator (provider-agnostic)
"""

from __future__ import annotations

import functools
import os
import random
import threading
import time
from typing import Callable, Tuple, Type, Any


# ────────────────────────────── bucket ──────────────────────────────
class _TokenBucket:
    def __init__(self, rpm: int):
        self.capacity = max(1, rpm)
        self.tokens = self.capacity
        self.lock = threading.Lock()
        self.last = time.time()

    def _refill(self) -> None:
        now = time.time()
        if now - self.last >= 60:
            self.tokens = self.capacity
            self.last = now

    def consume(self) -> None:
        with self.lock:
            self._refill()
            if self.tokens == 0:
                sleep = 60 - (time.time() - self.last)
                time.sleep(max(0.0, sleep))
                self._refill()
            self.tokens -= 1


TOKEN_BUCKET = _TokenBucket(int(os.getenv("GLOBAL_MAX_RPM", "10")))

# ─────────────────────── retry decorator ────────────────────────────
def retry_on_rate_limit(
    *,
    errors: Tuple[Type[Exception], ...],
    max_retries_env: str,
    default_max_retries: int = 3,
    get_delay: Callable[[Exception, int], float] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Example::

        @retry_on_rate_limit(
            errors=(openai.RateLimitError,),
            max_retries_env="OPENAI_MAX_RETRIES",
            default_max_retries=3,
            get_delay=lambda e, n: e.retry_after or 2**n,
        )
        def generate(...): ...
    """
    max_retries = int(os.getenv(max_retries_env, default_max_retries))

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            TOKEN_BUCKET.consume()
            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except errors as err:
                    if attempt == max_retries:
                        raise
                    base = get_delay(err, attempt) if get_delay else 2**attempt
                    time.sleep(base + random.uniform(0, 0.5))

        return wrapper

    return decorator
