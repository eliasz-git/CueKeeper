"""CueKeeper application factory.

This is the single entry point used by ``uvicorn src.main:app`` and by the test
suite (which does ``import src.main`` and ``importlib.reload(src.main)``).

Route handling is delegated to the routers in ``src/routers/``; cross-cutting
concerns live in ``src/services/`` and ``src/middleware/``. This module keeps
only the app factory, lifespan, middleware registration, static mounts, and
``__version__`` (the single source of truth per VERSIONING.md).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .middleware.security import security_headers
from .routers import cues as cues_router
from .routers import websocket as websocket_router

# Single source of truth for the CueKeeper version (semver, pre-1.0: MAJOR=0).
# Everything else (README, package.json, release tags) is derived from this.
__version__ = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.audio_dir().mkdir(parents=True, exist_ok=True)
    app.state.manager = websocket_router.ConnectionManager()
    # Clean up orphaned .tmp files left by a previous crash.
    df = config.data_file()
    for tmp in df.parent.glob(df.name + ".*.tmp"):
        try:
            tmp.unlink()
        except OSError:
            pass
    if not df.exists():
        from .services.data import save_data

        await save_data({"cues": [], "next_id": 1})
    yield


app = FastAPI(lifespan=lifespan)

# Defense-in-depth headers on every HTTP response.
app.middleware("http")(security_headers)

# API routers.
app.include_router(cues_router.router)
app.include_router(websocket_router.router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# Static file serving: audio files at /audio, the SPA at /.
app.mount("/audio", StaticFiles(directory=config.audio_dir(), check_dir=False), name="audio")
app.mount("/", StaticFiles(directory=config.static_dir(), html=True), name="static")
