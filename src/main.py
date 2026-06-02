import json
import os
import shutil
from pathlib import Path

from fastapi import FastAPI, Form, UploadFile
from fastapi.staticfiles import StaticFiles

app = FastAPI()


@app.get("/api/cues")
def get_cues():
    with open("data.json") as f:
        data = json.load(f)
    return data["cues"]


@app.post("/api/cues")
def create_cue(name: str = Form(...), file: UploadFile = ...):
    # 1. Save the uploaded file to the audio/ folder
    file_path = Path("audio") / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Build the cue object
    cue = {
        "id": len(os.listdir("audio")),  # simple id
        "name": name,
        "file": file.filename,
    }

    # 3. Append to data.json
    with open("data.json", "r+") as f:
        data = json.load(f)
        data["cues"].append(cue)
        f.seek(0)
        json.dump(data, f, indent=2)

    return cue


app.mount("/", StaticFiles(directory="static", html=True), name="static")


@app.on_event("startup")
def startup():
    os.makedirs("audio", exist_ok=True)
    if not os.path.exists("data.json"):
        with open("data.json", "w") as f:
            json.dump({"cues": []}, f)


@app.get("/hello")
def hello():
    return {"message": "hello"}
