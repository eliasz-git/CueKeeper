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

Guidance for future use & best practices
- Prefer using AI for non-core logic: docs, commit messages, boilerplate, and idea prioritization.
- When using AI for code completions, always run tests and read the generated code line-by-line before committing.
- Keep a short log entry (use the template above) per AI session so you can truthfully quantify usage if asked.
- If AI produces code that touches security/auth/data-handling, escalate to manual review and add tests before committing.

Stardance / Submission tip
- Paste the one‑line declaration into the project README and the Stardance AI usage field.
- Attach one example log entry to your submission (the Example entry above is fine) so judges can see you were transparent.
