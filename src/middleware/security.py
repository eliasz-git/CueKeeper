"""Security headers applied to every HTTP response."""

from fastapi import Request, Response


async def security_headers(request: Request, call_next) -> Response:
    """Add defense-in-depth headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self'; "
        "connect-src 'self'; "
        "media-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return response
