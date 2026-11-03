"""Configuration and environment-driven constants for CueKeeper.

Values are read lazily from the environment on every call so that tests can
monkeypatch ``os.environ`` and reload ``src.main`` (without reloading
``src.config``) and still pick up the new settings.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def data_file():
    return Path(os.environ.get("CUEKEEPER_DATA", ROOT / "data.json"))


def audio_dir():
    return Path(os.environ.get("CUEKEEPER_AUDIO", ROOT / "audio"))


def static_dir():
    return ROOT / "static"


def audio_extensions():
    return {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".opus"}


def max_upload_size():
    return int(os.environ.get("CUEKEEPER_MAX_UPLOAD_MB", "50")) * 1024 * 1024


def cuekeeper_token():
    return os.environ.get("CUEKEEPER_TOKEN", "")


def cuekeeper_auth_required():
    return os.environ.get("CUEKEEPER_AUTH_REQUIRED", "true").lower() == "true"


def rate_limit_requests():
    return int(os.environ.get("CUEKEEPER_RATE_LIMIT_REQUESTS", "60"))


def rate_limit_window():
    return int(os.environ.get("CUEKEEPER_RATE_LIMIT_WINDOW", "60"))
