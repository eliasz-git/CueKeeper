"""Pydantic models describing the CueKeeper API resource shapes."""

from pydantic import BaseModel


class Cue(BaseModel):
    """A single sound cue."""

    id: int
    name: str
    file: str


class CueCreate(BaseModel):
    """Payload returned when a new cue is created."""

    id: int
    name: str
    file: str


class TriggerResponse(BaseModel):
    """Payload returned when a cue is triggered."""

    status: str
    cue: Cue


class Health(BaseModel):
    """Health-check response."""

    status: str = "ok"


class CueReorder(BaseModel):
    """Request body for reordering cues."""

    order: list[int]
