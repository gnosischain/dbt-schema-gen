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
from typing import Callable, Tuple, Type


# ────────────────────────────────────────────────────────────────────────────
# 1.  Global token bucket  (requests-per-minute)
# ────────────────────────────────────────────────────────────────────────────
class _TokenBucket:
    """Thread-safe token bucket limiting calls per minute."""

    def __init__(self, rpm: int):
        self.capacity = max(1, rpm)
        self.tokens = self.capacity
        self.lock = threading.Lock()
        self.last_refill = time.time()

    def consume(self) -> None:
        with self.lock:
            self._refill()
            if self.tokens == 0:
                sleep_time = 60 - (time.time() - self.last_refill)
                time.sleep(max(0.0, sleep_time))
                self._refill()
            self.tokens -= 1

    def _refill(self) -> None:
        now = time.time()
        if now - self.last_refill >= 60:
            self.tokens = self.capacity
            self.last_refill = now


# single global instance – rpm comes from env or defaults to 10
_GLOBAL_BUCKET = _TokenBucket(int(os.getenv("GLOBAL_MAX_RPM", "10")))


# ────────────────────────────────────────────────────────────────────────────
# 2.  Decorator factory
# ────────────────────────────────────────────────────────────────────────────
def retry_on_rate_limit(
    *,
    errors: Tuple[Type[Exception], ...],
    max_retries_env: str,
    default_max_retries: int = 3,
    get_delay: Callable[[Exception, int], float] | None = None,
) -> Callable[[Callable[..., str]], Callable[..., str]]:
    """
    Usage::

        @retry_on_rate_limit(
            errors=(RateLimitError,),
            max_retries_env="OPENAI_MAX_RETRIES",
            default_max_retries=3,
            get_delay=my_delay_fn,   # optional
        )
        def generate(...): ...
    """
    max_retries = int(os.getenv(max_retries_env, default_max_retries))

    def decorator(func: Callable[..., str]) -> Callable[..., str]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> str:  # type: ignore[override]
            # always pass through the global bucket first
            _GLOBAL_BUCKET.consume()

            for attempt in range(max_retries + 1):  # attempt 0 = first call
                try:
                    return func(*args, **kwargs)

                except errors as err:
                    if attempt == max_retries:
                        raise  # bubble up

                    # provider-specific delay hint or fallback
                    base_delay = (
                        get_delay(err, attempt) if get_delay else 2**attempt
                    )
                    jitter = random.uniform(0, 0.5)
                    time.sleep(base_delay + jitter)
                    continue

        return wrapper

    return decorator
