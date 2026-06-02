# CueKeeper
A lightweight web sound-cue manager for theater productions. Allows the user to load audio, sequence cues, and trigger locally or remotely from another device, like a phone, via WebSocket.

---
## Demo
None yet since im just starting this project, but I will post one here when I have something working.

---
## MVP Features:
- Upload an audio file via the UI
- Give it a name; the server stores it in ./audio and adds a cue to data.json
- From any device on the same LAN, open the same URL and press Play to trigger the cue.

## Config / env (optional)
- CUEKEEPER_TOKEN=***    # optional: simple remote auth
- PORT=8000

## Project Layout
```
.
├── audio/  # where uploaded audio files are stored
├── src/ # source code for the server
│   ├── main.py
├── static/ # static files served by the server
│   ├── index.html
├── tests/ # test scripts
├── .envexample # example env file
├── .gitignore
├── agents.md # notes on using AI agents to help with development
├── data.json # where cue metadata is stored
├── LICENSE
├── package.json
├── README.md
├── requirements.txt # for python dependencies
```

## AI Usage
I will only use AI for code completion, proofreading documentation, and to structure/prioritize feature ideas into actionable tasks. All AI suggestions were reviewed, edited, and tested by me.

## Tests
Run tests locally:

```bash
pytest -q
```

## Security note
This scaffold is LAN‑first and has no auth by default. If you plan to expose it beyond a trusted LAN, set CUEKEEPER_TOKEN and validate it server‑side before accepting play commands.

## License & contact
License: MIT
Contact: Elias (eliaspublic@icloud.com)
