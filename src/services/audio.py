"""Audio file validation and storage helpers."""

import asyncio
from pathlib import Path

from fastapi import HTTPException, UploadFile

from .. import config


def validate_audio_filename(filename: str | None) -> str:
    """Return a safe basename if the file has an allowed audio extension."""
    name = Path(filename or "").name
    if not name or Path(name).suffix.lower() not in config.audio_extensions():
        raise HTTPException(
            400,
            "Upload an audio file (" + ", ".join(sorted(config.audio_extensions())) + ")",
        )
    return name


async def read_upload(file: UploadFile) -> bytes:
    """Read an uploaded file and enforce the size limit."""
    contents = await file.read()
    if len(contents) > config.max_upload_size():
        raise HTTPException(
            413, f"File too large (max {config.max_upload_size() // (1024 * 1024)} MB)"
        )
    return contents


def unique_audio_path(filename: str) -> Path:
    """Return a non-colliding path under ``AUDIO_DIR`` for ``filename``."""
    path = config.audio_dir() / filename
    stem, suffix = path.stem, path.suffix
    n = 1
    while path.exists():
        path = config.audio_dir() / f"{stem}-{n}{suffix}"
        n += 1
    return path


async def write_file(path: Path, contents: bytes) -> None:
    """Blocking file write, meant to be run via asyncio.to_thread."""
    await asyncio.to_thread(_write_file_sync, path, contents)


def _write_file_sync(path: Path, contents: bytes) -> None:
    with open(path, "wb") as buffer:
        buffer.write(contents)
