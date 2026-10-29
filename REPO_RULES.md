# Repo Rules — CueKeeper

These are the working rules for the CueKeeper repository. They supplement `AGENTS.md` (agent-facing guidance) and `VERSIONING.md` (release policy).

## Core design rule

> **CueKeeper is LAN-first show control.** Every user-facing surface (web UI, WebSocket, API) runs on a trusted local network in a theater. Any new feature should respect that the operator is in a darkened booth, possibly on a phone, and that a mistake mid-show means silence or wrong audio at the wrong time.

## File rules

- **Do not commit `data.json` or `audio/`** — these are per-show state created on first run and are gitignored.
- **Do not commit `.venv/`, `.env`, `__pycache__/`, `.pytest_cache/`, or `.ruff_cache/`** — local environment/cache artifacts.
- **Do not commit `builds/`** — produced by `build_release.sh` and not part of the source tree.
- **Static assets (`static/`) are coupled to the UI.** When renaming `app.js` or `style.css`, update every reference in `index.html`.

## Before committing

Run both checks:

```bash
ruff check src tests
pytest -q
```

Then manually smoke-test the server: start `uvicorn src.main:app`, open `http://localhost:8000`, upload a cue, play it, and verify the WebSocket status shows "Connected".

Commit with the noreply identity: `117379918+tundra-node@users.noreply.github.com`

```bash
git commit -m "..." -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

## PRs

End pull request descriptions with:

```text
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## Branches

- Default branch is `main`. Do not commit directly to `main` for feature work; branch first.
- Use `gh` CLI for GitHub operations (PRs, issues, API).

## Versioning

See `VERSIONING.md`. One source of truth: `__version__` in `src/main.py`.

## Security rules (do not break)

- `CUEKEEPER_TOKEN` is enforced on all mutating endpoints and the WebSocket (fail-closed by default).
- `data.json` writes use a unique tmp file per save to prevent corruption under concurrent upload/delete.
- Uploads are size-capped (50 MB default) and extension-allowed.
- Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`) are set on all HTTP responses.
- Do not add wildcard CORS in production; same-origin LAN use only.