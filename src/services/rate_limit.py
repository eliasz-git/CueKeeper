"""Per-IP, per-path in-memory rate limiter."""

import time

from fastapi import HTTPException, Request

from .. import config

_rate_limits: dict[str, dict[str, list[float]]] = {}


def check_rate_limit(request: Request) -> None:
    """Raise HTTP 429 when the per-IP, per-path request limit is exceeded.

    The in-memory table is pruned of expired/idle entries on every request so it
    cannot grow without bound as new IPs and paths are observed over a long run.
    """
    ip = request.client.host if request.client else "unknown"
    path = request.url.path
    now = time.time()
    window = config.rate_limit_window()

    by_path = _rate_limits.setdefault(ip, {})
    stamps = by_path.get(path, [])
    stamps = [t for t in stamps if now - t < window]
    if len(stamps) >= config.rate_limit_requests():
        retry_after = max(1, int(window - (now - stamps[0])))
        raise HTTPException(
            429, "Rate limit exceeded", headers={"Retry-After": str(retry_after)}
        )
    stamps.append(now)
    by_path[path] = stamps

    # Drop idle entries whose timestamps have all fallen out of the window,
    # otherwise one permanent entry is created for every (ip, path) pair ever
    # seen and the table grows forever.
    for stale_ip in list(_rate_limits):
        paths = _rate_limits[stale_ip]
        for stale_path in list(paths):
            live = [t for t in paths[stale_path] if now - t < window]
            if live:
                paths[stale_path] = live
            else:
                del paths[stale_path]
        if not paths:
            del _rate_limits[stale_ip]
