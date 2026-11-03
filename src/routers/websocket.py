"""WebSocket connection manager and ``/ws`` broadcast endpoint."""

import json
import secrets

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from .. import config

router = APIRouter()


class ConnectionManager:
    """Tracks active WebSocket peers and broadcasts JSON messages to all of them.

    Peers that drop mid-broadcast are detected and dropped so dead connections
    cannot accumulate during a long run.
    """

    def __init__(self) -> None:
        self.active: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        payload = json.dumps(message)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:  # noqa: BLE001 — detect and drop dead WebSocket peers
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


def get_manager():
    """Dependency returning the :class:`ConnectionManager` stored on ``app.state``.

    The import of ``app`` is intentionaly lazy (inside the function body) to
    avoid a circular import: ``main.py`` imports this router, so importing
    ``app`` at module load time would fail while ``main.py`` is still executing.
    """
    from ..main import app

    return app.state.manager  # set in lifespan


@router.websocket("/ws")
async def ws(
    websocket: WebSocket,
    manager=Depends(get_manager),  # noqa: B008
):
    # Accept the handshake first (browsers can't set custom headers), then
    # validate the token. The peer is closed *before* being added to
    # ``manager.active``, so it can never receive broadcasts (fail-closed).
    await websocket.accept()
    if config.cuekeeper_auth_required() and not config.cuekeeper_token():
        await websocket.close(code=4401, reason="Authentication not configured")
        return
    if config.cuekeeper_token():
        # Browser WebSocket cannot set custom headers, so the token travels via
        # ?token= or the Sec-WebSocket-Protocol handshake header.
        token = websocket.query_params.get("token", "")
        protocols = websocket.headers.get("sec-websocket-protocol", "")
        if protocols:
            token = protocols.split(",")[0].strip()
        if not secrets.compare_digest(token, config.cuekeeper_token()):
            await websocket.close(code=4401, reason="Invalid token")
            return

    manager.active.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
