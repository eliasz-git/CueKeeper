# CueKeeper — Theater Sound Cue Manager

A lightweight, LAN-first web app for theater sound crews and stage managers.
Run it on the show computer, then trigger cues from a phone or tablet on the
same network over WebSocket — perfect for when the computer playing sound and
the person calling cues aren't in the same spot.

```
show computer  (CueKeeper server, http://<show-ip>:8000)
        |
        |  LAN (Wi-Fi / ethernet)
        |
phone / tablet  (remote: open http://<show-ip>:8000, press GO)
```

## Who this is for

- **Sound operators / stage managers** who need a simple, reliable way to fire
  sound cues from a phone or tablet backstage.
- **Theater techs** who want something that installs in minutes and runs on a
  trusted local network with no cloud accounts.
- **Contributors** — see [Developer setup](#developer-setup) below.

## Core features

- Upload audio cues (`.mp3`, `.wav`, `.ogg`, `.m4a`, `.aac`, `.flac`, `.opus`)
- Large, tactile **GO** button plus per-cue **Play / Delete**
- Real-time cue queue with **drag-to-reorder** (order is saved to the server)
- Playback **timer** (elapsed / duration) and **volume** control
- Active-cue highlighting so you always know what's playing
- **Connection status indicator** — the remote device instantly knows if it's
  synced with the show computer
- Keyboard shortcuts: `Space`/`Enter` = GO, `↑`/`↓` = navigate the cue list
- Token-authenticated remote triggering (`CUEKEEPER_TOKEN`)
- Dark "booth" theme tuned for low-light control booths

## Quick start (theater tech)

You need Python 3.11 or newer.

```bash
# 1. Clone/download this project, then open a terminal in the folder
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Copy the example env file and set a token (strongly recommended)
cp .envexample .env
# edit .env and set CUEKEEPER_TOKEN to a secret of your choice

# 3. Start the server
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Or use the npm shortcut (reads `PORT` from `.env`):

```bash
npm start
```

### Connecting from another device on the LAN

1. Find the show computer's local IP address:
   - macOS: `ipconfig getifaddr en0` (Wi-Fi) or `en1` (ethernet)
   - Linux: `hostname -I`
   - Windows: `ipconfig` (look for the IPv4 address on your LAN adapter)
   Example: `192.168.1.42`
2. On the phone/tablet connected to the **same Wi-Fi**, open:
   `http://192.168.1.42:8000`
3. Enter the access token (if you set one), then upload cues and press GO.

If it doesn't connect, see [Troubleshooting](#troubleshooting) below.

## Configuration (`.env`)

Copy `.envexample` to `.env` and adjust as needed:

```bash
cp .envexample .env
```

| Variable | Default | What it does |
|---|---|---|
| `CUEKEEPER_TOKEN` | (none) | Access token required on mutating endpoints and WebSocket. **Set this for any shared LAN.** |
| `CUEKEEPER_AUTH_REQUIRED` | `true` | When `true`, mutating endpoints/WebSocket fail closed unless a token is set. Set `false` only for isolated local dev. |
| `PORT` | `8000` | Port used by `npm start` |
| `CUEKEEPER_DATA` | `./data.json` | Cue metadata store (your show's state) |
| `CUEKEEPER_AUDIO` | `./audio` | Uploaded audio files |
| `CUEKEEPER_MAX_UPLOAD_MB` | `50` | Max upload size in megabytes |
| `CUEKEEPER_RATE_LIMIT_REQUESTS` | `60` | Requests per IP per path per window |
| `CUEKEEPER_RATE_LIMIT_WINDOW` | `60` | Rate-limit window in seconds |

`data.json` and `audio/` are created on first run and are **not tracked in git** —
they are your show's state. Back them up like any other show file.

### Token security

CueKeeper is designed for a **trusted LAN**. When `CUEKEEPER_TOKEN` is set, it is
enforced as `Authorization: Bearer <token>` on all mutating endpoints
(`POST /api/cues`, `DELETE /api/cues/{id}`, `POST /api/cues/{id}/trigger`,
`POST /api/cues/reorder`) and on the WebSocket (`/ws?token=...`). Without a
token, auth is disabled (local dev only).

Do not expose CueKeeper to the public internet. If you run on a shared network,
set `CUEKEEPER_TOKEN` and, ideally, put the service behind an authenticated
reverse proxy with TLS (use WSS for WebSocket).

## Using the UI

- **Upload a cue:** enter a name, choose an audio file, click Upload. Duplicate
  filenames get a `-1`, `-2`, … suffix so nothing is overwritten.
- **GO / Play:** the big red GO button plays the first cue in the queue. Click
  a cue's **Play** button to play that cue. `Space`/`Enter` also fires GO when
  you're not typing in a field.
- **Reorder:** drag a cue by the `⠿` handle to change its position. The new
  order is saved to the server immediately.
- **Timer / volume:** the playback timer shows elapsed / duration while a cue
  plays; use the volume slider and mute button to set levels.
- **Connection status:** the indicator in the header shows Connected /
  Disconnected — reconnecting. If it stays disconnected, the remote device
  can't receive triggers.

## Audio output troubleshooting (show machine)

CueKeeper plays audio through the show computer's **default output device**.
If you don't hear anything:

1. Check the show computer's volume isn't muted and is turned up.
2. In System Settings → Sound (macOS) or Sound settings (Windows/Linux),
   confirm the correct output device (e.g. built-in speakers, not a disconnected
   HDMI/airplay target) is selected.
3. Test by uploading a short cue and clicking **Play** directly on the show
   computer — the timer should advance and you should hear audio.
4. If using an external interface, select it as the system output device, or
   route CueKeeper's output to it in your OS audio settings.

## Developer setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Run quality checks and tests:

```bash
ruff check src tests
pytest -q
```

Project layout:

```
.
├── audio/              # uploaded audio (created on first run, not tracked)
├── src/
│   ├── __init__.py
│   ├── config.py       # env-driven configuration (lazy reads)
│   ├── main.py         # FastAPI app factory (__version__ single source of truth)
│   ├── models.py       # Pydantic resource shapes
│   ├── middleware/
│   │   └── security.py # defense-in-depth headers
│   ├── routers/
│   │   ├── cues.py     # CRUD, trigger, reorder
│   │   └── websocket.py# ConnectionManager + /ws broadcast
│   └── services/
│       ├── audio.py    # upload validation + storage
│       ├── auth.py     # bearer-token enforcement
│       ├── data.py     # data.json load/save with lock + atomic tmp
│       └── rate_limit.py
├── static/             # index.html, style.css, app.js (the SPA)
├── tests/test_basic.py # pytest suite (API, auth, WebSocket)
├── .envexample         # example env file
├── .gitignore
├── AGENTS.md           # AI usage log
├── REPO_RULES.md       # local quality/commit rules
├── VERSIONING.md       # release policy (__version__ is the source of truth)
├── package.json        # `npm start` shortcut
├── pyproject.toml      # pytest config
├── requirements.txt
└── requirements-dev.txt
```

`__version__` in `src/main.py` is the single source of truth; `package.json` and
release tags are derived from it (see `VERSIONING.md`).

## AI usage

I only use AI for code completion, proofreading documentation, and to
structure/prioritize feature ideas into actionable tasks. All AI suggestions
were reviewed, edited, and tested by me. Per-session details are logged in
[AGENTS.md](AGENTS.md).

## License & contact

License: MIT

Contact: Elias (eliaspublic@icloud.com)
