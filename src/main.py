import asyncio
import json
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = Path(os.environ.get("CUEKEEPER_DATA", ROOT / "data.json"))
AUDIO_DIR = Path(os.environ.get("CUEKEEPER_AUDIO", ROOT / "audio"))
STATIC_DIR = ROOT / "static"

# Single source of truth for the CueKeeper version (semver, pre-1.0: MAJOR=0).
# Everything else (README, package.json, release tags) is derived from this.
__version__ = "0.1.0"

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".opus"}
MAX_UPLOAD_SIZE = int(os.environ.get("CUEKEEPER_MAX_UPLOAD_MB", "50")) * 1024 * 1024

CUEKEEPER_TOKEN = os.environ.get("CUEKEEPER_TOKEN", "")
# When true (default), mutating endpoints and the WebSocket are rejected unless
# CUEKEEPER_TOKEN is set. Set to "false" to opt into insecure local-dev mode.
CUEKEEPER_AUTH_REQUIRED = os.environ.get("CUEKEEPER_AUTH_REQUIRED", "true").lower() == "true"
data_lock = asyncio.Lock()

# Simple in-memory rate limiter: {ip: {path: [timestamps]}}
_rate_limits: dict[str, dict[str, list[float]]] = {}
RATE_LIMIT_REQUESTS = int(os.environ.get("CUEKEEPER_RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW = int(os.environ.get("CUEKEEPER_RATE_LIMIT_WINDOW", "60"))


def _check_rate_limit(request: Request):
    """Per-IP, per-path rate limiter. Raises HTTP 429 when exceeded."""
    ip = request.client.host if request.client else "unknown"
    path = request.url.path
    now = time.time()

    window = _rate_limits.get(ip, {}).get(path, [])
    window = [t for t in window if now - t < RATE_LIMIT_WINDOW]
    if len(window) >= RATE_LIMIT_REQUESTS:
        retry_after = max(1, int(RATE_LIMIT_WINDOW - (now - window[0])))
        raise HTTPException(
            429, "Rate limit exceeded", headers={"Retry-After": str(retry_after)}
        )
    window.append(now)
    _rate_limits.setdefault(ip, {})[path] = window


async def load_data():
    if not DATA_FILE.exists():
        return {"cues": [], "next_id": 1}
    return await asyncio.to_thread(_load_data_sync)


def _load_data_sync():
    with open(DATA_FILE) as f:
        data = json.load(f)
    if "next_id" not in data:
        data["next_id"] = max((c["id"] for c in data["cues"]), default=0) + 1
    return data


async def save_data(data):
    await asyncio.to_thread(_save_data_sync, data)


def _save_data_sync(data):
    # Unique tmp file per save so concurrent writers cannot interleave into a
    # shared data.tmp and corrupt data.json on os.replace.
    tmp = DATA_FILE.parent / (
        DATA_FILE.name + f".{os.getpid()}.{time.time_ns()}.tmp"
    )
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(DATA_FILE)


def unique_audio_path(filename):
    path = AUDIO_DIR / filename
    stem, suffix = path.stem, path.suffix
    n = 1
    while path.exists():
        path = AUDIO_DIR / f"{stem}-{n}{suffix}"
        n += 1
    return path


def _write_file(path: Path, contents: bytes) -> None:
    """Blocking file write, meant to be run via asyncio.to_thread."""
    with open(path, "wb") as buffer:
        buffer.write(contents)


async def verify_token(request: Request):
    """Bearer-token authorization for mutating endpoints.

    Disabled when CUEKEEPER_TOKEN is unset (local dev). When set, every mutating
    request must include ``Authorization: Bearer <token>`` compared with
    ``secrets.compare_digest`` to prevent timing attacks.
    """
    if CUEKEEPER_AUTH_REQUIRED and not CUEKEEPER_TOKEN:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Authentication not configured: set CUEKEEPER_TOKEN",
        )
    if not CUEKEEPER_TOKEN:
        return
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            401,
            "Missing or invalid authorization header",
            headers={"WWW-Authenticate": 'Bearer realm="cuekeeper"'},
        )
    token = auth[len("Bearer ") :].strip()
    if not secrets.compare_digest(token, CUEKEEPER_TOKEN):
        raise HTTPException(
            401,
            "Invalid token",
            headers={"WWW-Authenticate": 'Bearer realm="cuekeeper"'},
        )


class ConnectionManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active.discard(websocket)

    async def broadcast(self, message: dict):
        payload = json.dumps(message)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:  # noqa: BLE001 — detect and drop dead WebSocket peers
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


def get_manager() -> ConnectionManager:
    """Dependency that returns the ConnectionManager stored on app.state."""
    return app.state.manager  # set in lifespan


@asynccontextmanager
async def lifespan(app):
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    app.state.manager = ConnectionManager()
    if not DATA_FILE.exists():
        await save_data({"cues": [], "next_id": 1})
    yield


app = FastAPI(lifespan=lifespan)

# CORS — permissive by design for LAN theater use; restrict origins in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
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


@app.get("/api/cues")
async def get_cues(
    request: Request,
    _: None = Depends(verify_token),
    __: None = Depends(_check_rate_limit),
):
    return (await load_data())["cues"]


@app.post("/api/cues", status_code=201)
async def create_cue(
    request: Request,
    name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    _: None = Depends(verify_token),
    __: None = Depends(_check_rate_limit),
):
    name = name.strip()
    if not name:
        raise HTTPException(400, "Cue name is required")

    filename = Path(file.filename or "").name
    if not filename or Path(filename).suffix.lower() not in AUDIO_EXTENSIONS:
        raise HTTPException(
            400, "Upload an audio file (" + ", ".join(sorted(AUDIO_EXTENSIONS)) + ")"
        )

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            413, f"File too large (max {MAX_UPLOAD_SIZE // (1024 * 1024)} MB)"
        )

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    file_path = unique_audio_path(filename)
    await asyncio.to_thread(_write_file, file_path, contents)

    async with data_lock:
        data = await load_data()
        cue_id = data["next_id"]
        data["next_id"] = cue_id + 1
        cue = {
            "id": cue_id,
            "name": name,
            "file": file_path.name,
        }
        data["cues"].append(cue)
        await save_data(data)

    return cue


@app.delete("/api/cues/{cue_id}", status_code=204)
async def delete_cue(
    cue_id: int,
    _: None = Depends(verify_token),
    __: None = Depends(_check_rate_limit),
):
    async with data_lock:
        data = await load_data()
        cues = [c for c in data["cues"] if c["id"] != cue_id]
        if len(cues) == len(data["cues"]):
            raise HTTPException(404, "Cue not found")
        data["cues"] = cues
        await save_data(data)


@app.post("/api/cues/{cue_id}/trigger")
async def trigger_cue(
    cue_id: int,
    _: None = Depends(verify_token),
    __: None = Depends(_check_rate_limit),
    manager: ConnectionManager = Depends(get_manager),  # noqa: B008
):
    async with data_lock:
        data = await load_data()
        cue = next((c for c in data["cues"] if c["id"] == cue_id), None)
        if not cue:
            raise HTTPException(404, "Cue not found")
    await manager.broadcast({"action": "play", "cue": cue})
    return {"status": "triggered", "cue": cue}


@app.websocket("/ws")
async def ws(
    websocket: WebSocket,
    manager: ConnectionManager = Depends(get_manager),  # noqa: B008
):
    await websocket.accept()
    # Fail-closed: no token configured but auth required — reject the socket.
    if CUEKEEPER_AUTH_REQUIRED and not CUEKEEPER_TOKEN:
        await websocket.close(code=4401, reason="Authentication not configured")
        return
    if CUEKEEPER_TOKEN:
        # Browser WebSocket cannot set custom headers, so the token travels via
        # ?token= or the Sec-WebSocket-Protocol handshake header.
        token = websocket.query_params.get("token", "")
        protocols = websocket.headers.get("sec-websocket-protocol", "")
        if protocols:
            token = protocols.split(",")[0].strip()
        if not secrets.compare_digest(token, CUEKEEPER_TOKEN):
            await websocket.close(code=4401, reason="Invalid token")
            return
    manager.active.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.active.discard(websocket)


@app.get("/hello")
def hello():
    return {"message": "hello"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


app.mount("/audio", StaticFiles(directory=AUDIO_DIR, check_dir=False), name="audio")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
