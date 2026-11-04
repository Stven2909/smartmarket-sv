"""Lightweight per-process request budget for the public Streamlit demo.

The Laravel principal is intentionally excluded. No background workers,
timers, database access, logs containing secrets, or periodic keepalive.
"""

import math
import os
import threading
import time
from collections import deque

STREAMLIT_RATE_LIMIT_ENV = "SMARTMARKET_STREAMLIT_RATE_LIMIT_PER_MINUTE"
DEFAULT_STREAMLIT_RPM = 60
WINDOW_SECONDS = 60.0

_lock = threading.Lock()
_requests: deque[float] = deque()


def configured_streamlit_rate_limit() -> int:
    """A malformed configuration must never accidentally disable protection."""
    raw = os.getenv(STREAMLIT_RATE_LIMIT_ENV, str(DEFAULT_STREAMLIT_RPM)).strip()
    try:
        configured = int(raw)
    except (ValueError, OverflowError):
        return DEFAULT_STREAMLIT_RPM
    if configured < 1 or configured > 600:
        return DEFAULT_STREAMLIT_RPM
    return configured


def streamlit_rate_limit_retry_after() -> int | None:
    """Return seconds to retry if the shared Streamlit budget is exhausted."""
    now = time.monotonic()
    limit = configured_streamlit_rate_limit()

    with _lock:
        # Constant upper memory bound, independent of traffic volume.
        while _requests and now - _requests[0] >= WINDOW_SECONDS:
            _requests.popleft()
        if len(_requests) >= limit:
            return max(1, math.ceil(WINDOW_SECONDS - (now - _requests[0])))
        _requests.append(now)
    return None


def reset_streamlit_rate_limit_for_tests() -> None:
    """Clear the process-local limiter only in controlled test environments."""
    with _lock:
        _requests.clear()
