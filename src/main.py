import json
import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Set

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = Path(os.environ.get("CUEKEEPER_DATA", ROOT / "data.json"))
AUDIO_DIR = Path(os.environ.get("CUEKEEPER_AUDIO", ROOT / "audio"))
STATIC_DIR = ROOT / "static"

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".opus"}


def load_data():
    if not DATA_FILE.exists():
        return {"cues": []}
    with open(DATA_FILE) as f:
        return json.load(f)


def save_data(data):
    tmp = DATA_FILE.with_suffix(".tmp")
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


class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

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
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app):
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        save_data({"cues": []})
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/api/cues")
def get_cues():
    return load_data()["cues"]


@app.post("/api/cues", status_code=201)
def create_cue(name: Annotated[str, Form()], file: Annotated[UploadFile, File()]):
    name = name.strip()
    if not name:
        raise HTTPException(400, "Cue name is required")

    filename = Path(file.filename or "").name
    if not filename or Path(filename).suffix.lower() not in AUDIO_EXTENSIONS:
        raise HTTPException(400, "Upload an audio file (" + ", ".join(sorted(AUDIO_EXTENSIONS)) + ")")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    file_path = unique_audio_path(filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    data = load_data()
    cue = {
        "id": max((c["id"] for c in data["cues"]), default=0) + 1,
        "name": name,
        "file": file_path.name,
    }

    data["cues"].append(cue)
    save_data(data)

    return cue


@app.delete("/api/cues/{cue_id}", status_code=204)
def delete_cue(cue_id: int):
    data = load_data()
    cues = [c for c in data["cues"] if c["id"] != cue_id]
    if len(cues) == len(data["cues"]):
        raise HTTPException(404, "Cue not found")
    data["cues"] = cues
    save_data(data)


@app.post("/api/cues/{cue_id}/trigger")
async def trigger_cue(cue_id: int):
    data = load_data()
    cue = next((c for c in data["cues"] if c["id"] == cue_id), None)
    if not cue:
        raise HTTPException(404, "Cue not found")
    await manager.broadcast({"action": "play", "cue": cue})
    return {"status": "triggered", "cue": cue}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/hello")
def hello():
    return {"message": "hello"}


app.mount("/audio", StaticFiles(directory=AUDIO_DIR, check_dir=False), name="audio")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
