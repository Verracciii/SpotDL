"""Rate limiting, randomized jitter delays, and exponential backoff."""

from __future__ import annotations

import logging
import random
import time

from dj_downloader.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Manages cooldown intervals between downloads to prevent IP rate-limiting."""

    def __init__(
        self,
        min_delay: float | None = None,
        max_delay: float | None = None,
        base_backoff: float = 4.0,
    ) -> None:
        self.min_delay = min_delay if min_delay is not None else settings.min_delay_seconds
        self.max_delay = max_delay if max_delay is not None else settings.max_delay_seconds
        self.base_backoff = base_backoff

    def wait(self) -> float:
        """Sleep for a randomized duration between min_delay and max_delay."""
        if self.max_delay <= 0 or self.min_delay < 0:
            return 0.0

        delay = random.uniform(self.min_delay, self.max_delay)
        logger.debug(f"Applying rate-limit cooldown: sleeping {delay:.2f}s")
        time.sleep(delay)
        return delay

    def backoff(self, attempt: int) -> float:
        """Apply exponential backoff with jitter on rate-limit errors."""
        delay = float((self.base_backoff * (2 ** (attempt - 1))) + random.uniform(0.5, 2.0))
        logger.warning(f"Rate limit hit! Backing off for {delay:.2f}s (attempt {attempt})...")
        time.sleep(delay)
        return delay
