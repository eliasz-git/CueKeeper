"""Cue CRUD and triggering endpoints."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)

from .. import config
from ..models import Cue, CueReorder, TriggerResponse
from ..services.audio import (
    read_upload,
    unique_audio_path,
    validate_audio_filename,
    write_file,
)
from ..services.auth import verify_token
from ..services.data import data_lock, load_data, save_data
from ..services.rate_limit import check_rate_limit
from .websocket import get_manager

router = APIRouter()


@router.get("/api/cues", response_model=list[Cue])
async def get_cues(
    request: Request,
    _: None = Depends(verify_token),
    __: None = Depends(check_rate_limit),
):
    return (await load_data())["cues"]


@router.post("/api/cues", status_code=201, response_model=Cue)
async def create_cue(
    request: Request,
    name: str = Form(...),
    file: Annotated[UploadFile, File()] = ...,
    _: None = Depends(verify_token),
    __: None = Depends(check_rate_limit),
):
    name = name.strip()
    if not name:
        raise HTTPException(400, "Cue name is required")

    filename = validate_audio_filename(file.filename)
    contents = await read_upload(file)

    config.audio_dir().mkdir(parents=True, exist_ok=True)
    file_path = unique_audio_path(filename)
    await write_file(file_path, contents)

    async with data_lock:
        data = await load_data()
        cue_id = data["next_id"]
        data["next_id"] = cue_id + 1
        cue = {"id": cue_id, "name": name, "file": file_path.name}
        data["cues"].append(cue)
        await save_data(data)

    return cue


@router.delete("/api/cues/{cue_id}", status_code=204)
async def delete_cue(
    cue_id: int,
    _: None = Depends(verify_token),
    __: None = Depends(check_rate_limit),
):
    async with data_lock:
        data = await load_data()
        cues = [c for c in data["cues"] if c["id"] != cue_id]
        if len(cues) == len(data["cues"]):
            raise HTTPException(404, "Cue not found")
        data["cues"] = cues
        await save_data(data)


@router.post("/api/cues/{cue_id}/trigger", response_model=TriggerResponse)
async def trigger_cue(
    cue_id: int,
    _: None = Depends(verify_token),
    __: None = Depends(check_rate_limit),
    manager=Depends(get_manager),  # noqa: B008
):
    async with data_lock:
        data = await load_data()
        cue = next((c for c in data["cues"] if c["id"] == cue_id), None)
        if not cue:
            raise HTTPException(404, "Cue not found")
    await manager.broadcast({"action": "play", "cue": cue})
    return {"status": "triggered", "cue": cue}


@router.post("/api/cues/reorder", response_model=list[Cue])
async def reorder_cues(
    request: Request,
    reorder: CueReorder,
    _: None = Depends(verify_token),
    __: None = Depends(check_rate_limit),
):
    """Persist a new cue order. ``reorder.order`` is the list of cue ids in the
    desired sequence; the stored array order defines the display/queue order."""
    order = reorder.order
    async with data_lock:
        data = await load_data()
        by_id = {c["id"]: c for c in data["cues"]}
        if len(order) != len(data["cues"]) or set(order) != set(by_id):
            raise HTTPException(400, "Invalid cue order")
        data["cues"] = [by_id[cue_id] for cue_id in order]
        await save_data(data)
    return data["cues"]
