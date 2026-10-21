"""Tests for rate limiter and cooldown management."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from dj_downloader.limiter import RateLimiter


@patch("time.sleep")
def test_rate_limiter_wait(mock_sleep: MagicMock) -> None:
    limiter = RateLimiter(min_delay=2.0, max_delay=5.0)
    delay = limiter.wait()

    assert 2.0 <= delay <= 5.0
    mock_sleep.assert_called_once_with(delay)


@patch("time.sleep")
def test_rate_limiter_backoff(mock_sleep: MagicMock) -> None:
    limiter = RateLimiter(base_backoff=4.0)

    # Attempt 1
    delay1 = limiter.backoff(attempt=1)
    assert delay1 >= 4.0

    # Attempt 2 should be larger than base
    delay2 = limiter.backoff(attempt=2)
    assert delay2 >= 8.0
