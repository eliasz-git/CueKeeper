# CueKeeper
A lightweight web sound-cue manager for theater productions. Allows the user to load audio, sequence cues, and trigger locally or remotely from another device, like a phone, via WebSocket.

I'm building it for the sound crew on a school/community theater show, where the computer playing sound and the person calling cues aren't always in the same spot.

---
## Status
Early. The server side of cue storage works; the web UI and remote triggering are not built yet.

| Feature | Status |
| --- | --- |
| Upload an audio file with a cue name (`POST /api/cues`) | Done |
| List cues (`GET /api/cues`) | Done |
| Serve uploaded audio (`/audio/<file>`) | Done |
| Web UI for uploading and playing cues | Not started (placeholder page) |
| Trigger a cue from another device over WebSocket | Not started |
| Cue ordering / GO button | Not started |
| Token auth for remote triggers (`CUEKEEPER_TOKEN`) | Not started |

---
## Demo
None yet since im just starting this project, but I will post one here when I have something working.

---
## MVP Features:
- Upload an audio file via the UI
- Give it a name; the server stores it in ./audio and adds a cue to data.json
- From any device on the same LAN, open the same URL and press Play to trigger the cue.

## Quick start
Needs Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` on the show computer, or `http://<computer-ip>:8000` from another device on the same network. `npm start` runs the same command with auto-reload and reads `PORT`.

Add a cue from the command line until the UI exists:

```bash
curl -F name="Thunder" -F file=@thunder.mp3 http://localhost:8000/api/cues
curl http://localhost:8000/api/cues
```

Uploads must be audio files (`.mp3 .wav .ogg .m4a .aac .flac .opus`). If a file with the same name already exists, the new one is saved as `name-1.mp3` and so on.

## Config / env (optional)
| Variable | Default | What it does |
| --- | --- | --- |
| `PORT` | `8000` | Port used by `npm start` |
| `CUEKEEPER_DATA` | `./data.json` | Where cue metadata is stored |
| `CUEKEEPER_AUDIO` | `./audio` | Where uploaded audio is stored |
| `CUEKEEPER_TOKEN` | (none) | Planned: simple remote auth. Not read yet. |

`data.json` and `audio/` are your show's state. They are created on first run and are not tracked in git.

## Project Layout
```
.
├── audio/              # uploaded audio files (created on first run, not tracked)
├── src/                # source code for the server
│   └── main.py
├── static/             # static files served by the server
│   └── index.html
├── tests/              # pytest suite
├── .github/workflows/  # CI: ruff + pytest
├── .envexample         # example env file
├── agents.md           # notes on using AI agents to help with development
├── data.json           # cue metadata (created on first run, not tracked)
├── LICENSE
├── package.json        # npm start shortcut
├── pyproject.toml      # pytest config
├── requirements.txt    # python dependencies
└── requirements-dev.txt
```

## AI Usage
I will only use AI for code completion, proofreading documentation, and to structure/prioritize feature ideas into actionable tasks. All AI suggestions were reviewed, edited, and tested by me.

Per-session details are logged in [agents.md](agents.md).

## Tests
Run tests locally:

```bash
pip install -r requirements-dev.txt
ruff check src tests
pytest -q
```

## Security note
This scaffold is LAN‑first and has no auth by default. If you plan to expose it beyond a trusted LAN, set CUEKEEPER_TOKEN and validate it server‑side before accepting play commands. Token checking is not implemented yet, so do not expose it beyond a trusted LAN for now.

## License & contact
License: MIT
Contact: Elias (eliaspublic@icloud.com)
