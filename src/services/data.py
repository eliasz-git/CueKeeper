"""Persistent state management for ``data.json``.

All reads/writes are offloaded to a thread pool so the event loop never blocks
on disk I/O. A single :data:`data_lock` serializes read-modify-write cycles so
concurrent upload/delete/trigger operations cannot interleave and corrupt the
store. Each save writes to a unique temporary file before ``os.replace`` so two
concurrent saves cannot interleave into a shared tmp file.
"""

import asyncio
import json
import os
import time

from .. import config

data_lock = asyncio.Lock()


def _load_data_sync(data_file) -> dict:
    with open(data_file) as f:
        data = json.load(f)
    if "next_id" not in data:
        data["next_id"] = max((c["id"] for c in data["cues"]), default=0) + 1
    return data


async def load_data() -> dict:
    """Load the cue store, returning a fresh empty store if the file is absent."""
    data_file = config.data_file()
    if not data_file.exists():
        return {"cues": [], "next_id": 1}
    return await asyncio.to_thread(_load_data_sync, data_file)


def _save_data_sync(data: dict, data_file) -> None:
    tmp = data_file.parent / (
        data_file.name + f".{os.getpid()}.{time.time_ns()}.tmp"
    )
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(data_file)


async def save_data(data: dict) -> None:
    """Atomically persist ``data`` to the configured data file."""
    data_file = config.data_file()
    await asyncio.to_thread(_save_data_sync, data, data_file)
