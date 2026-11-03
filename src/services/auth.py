"""Bearer-token authorization for mutating endpoints and WebSocket connections."""

import secrets

from fastapi import HTTPException, Request, status

from .. import config


async def verify_token(request: Request) -> None:
    """Authorize a mutating request with ``Authorization: Bearer <token>``.

    Disabled when ``CUEKEEPER_TOKEN`` is unset (local dev). When
    ``CUEKEEPER_AUTH_REQUIRED`` is true but no token is configured, fail closed
    with 503. Token comparison uses ``secrets.compare_digest``.
    """
    if config.cuekeeper_auth_required() and not config.cuekeeper_token():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Authentication not configured: set CUEKEEPER_TOKEN",
        )
    if not config.cuekeeper_token():
        return
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            401,
            "Missing or invalid authorization header",
            headers={"WWW-Authenticate": 'Bearer realm="cuekeeper"'},
        )
    token = auth[len("Bearer ") :].strip()
    if not secrets.compare_digest(token, config.cuekeeper_token()):
        raise HTTPException(
            401,
            "Invalid token",
            headers={"WWW-Authenticate": 'Bearer realm="cuekeeper"'},
        )
