"""Per-IP, per-path in-memory rate limiter."""

import time

from fastapi import HTTPException, Request

from .. import config

_rate_limits: dict[str, dict[str, list[float]]] = {}


def check_rate_limit(request: Request) -> None:
    """Raise HTTP 429 when the per-IP, per-path request limit is exceeded."""
    ip = request.client.host if request.client else "unknown"
    path = request.url.path
    now = time.time()

    window = _rate_limits.get(ip, {}).get(path, [])
    window = [t for t in window if now - t < config.rate_limit_window()]
    if len(window) >= config.rate_limit_requests():
        retry_after = max(1, int(config.rate_limit_window() - (now - window[0])))
        raise HTTPException(
            429, "Rate limit exceeded", headers={"Retry-After": str(retry_after)}
        )
    window.append(now)
    _rate_limits.setdefault(ip, {})[path] = window
