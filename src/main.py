import json
import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
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

    # Drop any directory parts so uploads can't escape the audio folder
    filename = Path(file.filename or "").name
    if not filename or Path(filename).suffix.lower() not in AUDIO_EXTENSIONS:
        raise HTTPException(400, "Upload an audio file (" + ", ".join(sorted(AUDIO_EXTENSIONS)) + ")")

    # 1. Save the uploaded file to the audio/ folder without overwriting another cue's file
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    file_path = unique_audio_path(filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Build the cue object
    data = load_data()
    cue = {
        "id": max((c["id"] for c in data["cues"]), default=0) + 1,
        "name": name,
        "file": file_path.name,
    }

    # 3. Append to data.json
    data["cues"].append(cue)
    save_data(data)

    return cue


@app.get("/hello")
def hello():
    return {"message": "hello"}


app.mount("/audio", StaticFiles(directory=AUDIO_DIR, check_dir=False), name="audio")
# Mounted last: a mount at "/" catches every path, so routes declared after it never match
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
