# CueKeeper Security Audit Report

**Project:** CueKeeper — theater sound-cue manager (FastAPI + vanilla JS)  
**Scope:** `src/main.py`, `static/app.js`, `static/index.html`, `tests/test_basic.py`, `.envexample`, `.gitignore`  
**Deployment context:** Local-area network (LAN) in a theater; multiple operators/crew on the same subnet; show-control use where audio playback timing is production-critical.

## Rating scale

| Severity | Meaning |
|----------|---------|
| Critical | Complete authorization bypass; any LAN host can alter show state. |
| High | Exploitable by any LAN host to disrupt playback, corrupt data, or exhaust resources. |
| Medium | Exploitable under specific conditions or weakens defense-in-depth. |
| Low | Hygiene / hardening issues; limited direct exploitability. |

## Executive summary

CueKeeper has **no authentication or authorization layer**, despite `CUEKEEPER_TOKEN` being defined in `.envexample`. Every state-changing endpoint — cue upload, deletion, triggering — and the WebSocket broadcast channel are open to any device on the LAN. In a theater this means any crew phone, guest device, or compromised host can delete cues, fire audio at the wrong moment, fill the disk, or corrupt `data.json`. Not safe to deploy on a shared network until auth, input validation, and concurrency controls are added.
## Critical

### C-01 — No auth/token enforcement on mutating endpoints (CUEKEEPER_TOKEN defined but never enforced)

**File:line:** `src/main.py:85–110` (`create_cue`), `src/main.py:113–120` (`delete_cue`), `src/main.py:123–130` (`trigger_cue`); `.envexample:1`

**Vulnerable / missing code:** `CUEKEEPER_TOKEN` is never read via `os.environ`. None of the mutating routes use FastAPI dependencies (`Depends`), header checks, or token comparison:

```python
@app.delete("/api/cues/{cue_id}", status_code=204)
def delete_cue(cue_id: int):          # no auth check
    ...
@app.post("/api/cues/{cue_id}/trigger")
async def trigger_cue(cue_id: int):   # no auth check
    ...
@app.post("/api/cues", status_code=201)
def create_cue(name: ..., file: ...): # no auth check
    ...
```

**Risk (theater/LAN):** Any device on the LAN can `DELETE` cues mid-show, `POST /trigger` to fire audio at the wrong time, or upload new cues to clutter the stack. Total authorization bypass of the core show-control surface.

**Remediation:** Read `CUEKEEPER_TOKEN` at startup (fail closed if missing). Require `Authorization: Bearer <token>` on all mutating routes (and `GET /api/cues`). Compare with `secrets.compare_digest`; return `401`/`403` on mismatch. Add tests asserting `401` when the header is absent/wrong.

## High

### H-01 — WebSocket `/ws` accepts connections with no origin or token validation

**File:line:** `src/main.py:43–66` (`ConnectionManager`), `src/main.py:133–140` (`ws`); `static/app.js:12–15`

**Vulnerable / missing code:** `connect()` calls `await websocket.accept()` unconditionally before any inspection:

```python
async def connect(self, websocket: WebSocket):
    await websocket.accept()      # no origin, no token check
    self.active.add(websocket)
```

The client opens the socket to the same host with no credentials (`static/app.js:14`).

**Risk (theater/LAN):** Any LAN host can connect to `/ws` and receive the broadcast play payload (`{"action": "play", "cue": ...}`). An attacker can trigger playback on every connected tech table, or hold many connections open to exhaust the connection set. An unauthenticated WebSocket participant becomes a remote show-control actor.

**Remediation:** Require the same token (via query param `?token=` or header) and validate `websocket.headers.get("origin")` against expected LAN hosts *before* `accept()`. Reject with `await websocket.close(code=1008)` on failure. Prune dead sockets promptly (already done in `broadcast`).

### H-02 — File upload validates extension only; no size limit, content-type check, or magic-byte verification

**File:line:** `src/main.py:85–110` (esp. 91–93, 97–98); `static/index.html:20`

**Vulnerable / missing code:**

```python
filename = Path(file.filename or "").name                        # line 91
if not filename or Path(filename).suffix.lower() not in AUDIO_EXTENSIONS:  # line 92–93
    ...
with open(file_path, "wb") as buffer:                            # line 97
    shutil.copyfileobj(file.file, buffer)                        # line 98 — unbounded
```

`accept="audio/*"` in `static/index.html:20` is client-side only and bypassable. No `file.content_type` validation, no magic-byte (file-signature) check, no upload size cap.

**Risk (theater/LAN):** Unbounded `copyfileobj` lets any LAN host fill the disk → show computer crash. A `.mp3`-named file containing HTML/JS or a polyglot can be uploaded and served from `/audio`; MIME sniffing or direct URL access introduces XSS/content-execution risk. Non-audio binaries consume storage needed for the show.

**Remediation:** Enforce a maximum upload size (e.g., 50 MB) by streaming in chunks and aborting early. Validate `file.content_type` against audio MIME types and verify magic bytes (e.g., `python-magic` or manual header inspection for ID3/RIFF/Ogg/FLAC). Reject double extensions and dotfiles. Serve uploads with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`, or serve through an authenticated endpoint rather than a raw static mount.

### H-03 — `data.json` read-modify-write without locking; non-atomic ID generation

**File:line:** `src/main.py:19–30`, `src/main.py:85–108`, `src/main.py:113–120`

**Vulnerable / missing code:** `load_data()` and `save_data()` are separate, non-atomic operations with no file lock or asyncio lock. ID generation is `max(...) + 1` (`src/main.py:102`) computed outside any critical section. Under concurrent requests two writers can both read the same state and overwrite each other (lost update), producing duplicate IDs and lost cues.

**Risk (theater/LAN):** A stage manager deleting a cue while an operator uploads another can lose the deletion or the upload. Cue-list corruption mid-show makes `DELETE`/`trigger` ambiguous (duplicate IDs) and can cause wrong audio to fire or cues to vanish.

**Remediation:** Wrap the entire read-modify-write in an `asyncio.Lock` and, for multi-process safety, an `fcntl.flock` on `data.json` for the duration of load → save. Generate IDs under the same lock. For a show-control app, consider replacing `data.json` with SQLite (transactional, concurrent-safe).

### H-04 — No rate limiting on any endpoint

**File:line:** `src/main.py` (all routes; no middleware); `tests/test_basic.py` (no rate-limit tests)

**Vulnerable / missing code:** No rate-limiting middleware (e.g., `slowapi`) on `POST /api/cues`, `POST /api/cues/{id}/trigger`, or `DELETE /api/cues/{id}`.

**Risk (theater/LAN):** Unlimited uploads compound H-02 into a reliable disk-exhaustion DoS. Unlimited trigger requests spam the WebSocket broadcast, causing continuous audio playback. Sequential integer cue IDs (`1, 2, 3 …`) make enumeration trivial once auth is added, enabling brute-force guessing of cue IDs.

**Remediation:** Add rate limiting keyed by IP (and by authenticated user once auth exists): strict limits on upload/trigger/delete (e.g., 10–30/min), relaxed limits on `GET /api/cues`. Return `429` with `Retry-After`.

## Medium

### M-01 — Path traversal mitigation relies on `Path().name`; assumption undocumented

**File:line:** `src/main.py:91`; verified by `tests/test_basic.py:62–67`

**Vulnerable / missing code:**

```python
filename = Path(file.filename or "").name   # line 91 — strips "../../evil.mp3" → "evil.mp3"
```

The test confirms traversal is stripped, but the code contains no comment explaining why `Path.name` is the guard, and there is no secondary filename allowlist.

**Risk (theater/LAN):** If the assumption breaks (future code joins `filename` with a different base, Windows reserved names like `CON`/`PRN`, unusual Unicode), an attacker could write outside `AUDIO_DIR` and overwrite `data.json`, source files, or system files.

**Remediation:** Keep `Path.name` but add an explicit allowlist regex such as `^[A-Za-z0-9_.-]+$`, reject dotfiles and reserved names, and document the control in a comment above line 91 so future maintainers don't weaken it.

### M-02 — Atomic save via tmp+replace shares a fixed tmp filename (race window)

**File:line:** `src/main.py:26–30`

**Vulnerable / missing code:**

```python
def save_data(data):
    tmp = DATA_FILE.with_suffix(".tmp")   # fixed: data.tmp
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(DATA_FILE)                # atomic replace, but tmp is shared
```

`os.replace` is atomic, but two concurrent `save_data()` calls interleave writes into the *same* `data.tmp` before one replaces `data.json`. The surviving replace can contain mixed/corrupt content from both writers.

**Risk (theater/LAN):** Concurrent upload + delete (common during a show) can corrupt `data.json`, causing cue loss or application errors on next load.

**Remediation:** Use a unique temporary file per save (`tempfile.NamedTemporaryFile(dir=DATA_FILE.parent, delete=False)`) then `os.replace`, or hold the global write lock for the entire save. Clean up orphaned `.tmp` files on startup.

## Low

### L-01 — `/hello` debug route exposed

**File:line:** `src/main.py:143–145`; `tests/test_basic.py:80–81`

**Vulnerable / missing code:** A debug endpoint returns `{"message": "hello"}` with no authorization and is covered by a test (`test_hello_route_is_reachable`).

**Risk (theater/LAN):** Minimal direct impact, but it confirms the server is reachable and reveals framework details, aiding reconnaissance. Debug routes should not ship in production.

**Remediation:** Remove `/hello` or gate it behind an admin token / debug flag. Remove the test or mark it conditional.

### L-02 — CORS absent (fine for LAN but note it)

**File:line:** `src/main.py` — no `CORSMiddleware` added.

**Vulnerable / missing code:** No CORS policy is configured.

**Risk (theater/LAN):** On a LAN this is acceptable since the UI is served from the same origin. If the UI is ever served from a different origin, browsers will block cross-origin requests unless CORS is explicitly configured. Do not add wildcard `*` CORS in production.

**Remediation:** Keep CORS absent for same-origin LAN use. If cross-origin is needed later, restrict `allow_origins` to known hosts and require credentials only with auth.

### L-03 — No security headers

**File:line:** `src/main.py` — no middleware sets `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`.

**Risk (theater/LAN):** Static file serving (`/audio`, `/`) lacks `X-Content-Type-Options: nosniff`, increasing MIME-sniffing risk for uploaded files (see H-02).

**Remediation:** Add middleware to set `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and a basic `Content-Security-Policy`.

## Recommended priority order

1. **C-01** — Enforce `CUEKEEPER_TOKEN` on all mutating routes + WebSocket.
2. **H-01** — Add token + origin validation before `websocket.accept()`.
3. **H-02** — Add upload size cap, content-type + magic-byte validation.
4. **H-03** — Add `asyncio.Lock` + `fcntl.flock` around `data.json` read-modify-write.
5. **H-04** — Add rate limiting.
6. **M-01 / M-02** — Harden filename allowlist and unique tmp file per save.
7. **L-01 / L-02 / L-03** — Remove `/hello`, add security headers, document CORS stance.

