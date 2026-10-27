# Agents / AI usage log — CueKeeper

Purpose
- Record how AI tools were used on this project and provide a small provenance template you can reference for Stardance submission or future audits.

Official one‑line AI declaration (ready to paste)
- AI usage: Used AI for code completion, proofreading documentation, and to structure/prioritize feature ideas into actionable tasks. All AI suggestions were reviewed, edited, and tested by me.

Detailed log template (fill this out when you use AI)
- Date: YYYY-MM-DD
- Tool: (e.g. ChatGPT, GitHub Copilot, Copilot CLI)
- Purpose: (code completion / proofreading / brainstorming structuring / debugging)
- Files affected: (list paths or 'README only')
- Approx. % of content affected: (e.g. 3% / 0% if only phrasing)
- Verification: (tests run / manual review / linters) — include commit hashes if relevant
- Notes: (anything reviewers should know; e.g. "used to suggest folder layout, I changed it")

Example entry (fill-in for initial scaffold)
- Date: 2026-06-02
- Tool: unspecified AI tools (code completion + text assistant)
- Purpose: code completion, README phrasing, turning brainstorm bullet list into milestone tasks
- Files affected: initial scaffold files under CueKeeper/ (later removed) and README draft
- Approx. %: ~5% (mostly phrasing + small completions), code suggestions were reviewed and edited
- Verification: manual review, basic local smoke tests; no AI output was committed without human edits
- Notes: kept AI usage minimal and focused on non-core algorithmic work; primary logic authored by me.

Log entries
- Date: 2026-10-26
- Tool: opencode agent (Claude)
- Purpose: debugging, tests, repo hygiene, README update
- Files affected: src/main.py (upload path traversal fix, id/file collision fix, route order fix, env-configurable paths), tests/test_basic.py (new suite), pyproject.toml, requirements*.txt, package.json, .gitignore, .github/workflows/ci.yml, README.md
- Approx. % of content affected: most of src/main.py was edited; no new features (UI, WebSocket triggering) were written
- Verification: pytest (13 passed), ruff, manual uvicorn + curl smoke test
- Notes: data.json untracked since it is per-show state the server writes
- Date: 2026-10-27
- Tool: opencode agent (Claude)
- Purpose: build web UI, WebSocket triggering, GO button, delete and trigger endpoints
- Files affected: src/main.py (DELETE /api/cues/{id}, POST /api/cues/{id}/trigger, WebSocket /ws, ConnectionManager), static/index.html (cue list, upload form, play/delete/GO buttons), static/style.css, static/app.js (fetch API, WebSocket client, audio playback), tests/test_basic.py (delete, trigger, websocket tests)
- Approx. % of content affected: ~30% (new UI + WebSocket layer)
- Verification: pytest (18 passed)
- Notes: WebSocket broadcast on trigger so remote clients can play cues; static served at "/" via StaticFiles

Guidance for future use & best practices
- Prefer using AI for non-core logic: docs, commit messages, boilerplate, and idea prioritization.
- When using AI for code completions, always run tests and read the generated code line-by-line before committing.
- Keep a short log entry (use the template above) per AI session so you can truthfully quantify usage if asked.
- If AI produces code that touches security/auth/data-handling, escalate to manual review and add tests before committing.

Stardance / Submission tip
- Paste the one‑line declaration into the project README and the Stardance AI usage field.
- Attach one example log entry to your submission (the Example entry above is fine) so judges can see you were transparent.
