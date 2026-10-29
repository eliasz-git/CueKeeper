# Skill: Frontend Audit

Purpose: A reusable, structured skill for auditing everything facing the user in a web application — HTML, CSS, JavaScript, accessibility, UX, client-side security, performance, and error handling. Designed for single-page apps, server-rendered UIs, and hybrid frontends like CueKeeper (FastAPI + vanilla JS).

Use this skill when you need to review a frontend before release, after a UI change, or as part of a security/UX audit.

---

## 1. Scope

Audit everything a human user sees and interacts with:

| Layer | What to check |
|-------|---------------|
| HTML | Semantic structure, labels, ARIA, meta tags, CSP, skip links, forms |
| CSS | Theme/contrast, focus states, touch targets, dark-mode support, responsive breakpoints |
| JavaScript | Error handling, XSS, auth token storage, WebSocket resilience, audio/media, event listeners |
| Accessibility | WCAG contrast, keyboard navigation, screen-reader friendliness, ARIA live regions |
| UX | Feedback/status messages, empty states, destructive-action confirmation, dark-booth/field usability |
| Client-side security | XSS injection points, token exposure, CSRF, CSP, referrer policy, SRI |
| Performance | Asset sizes, render-blocking resources, audio memory cleanup, reconnect backoff |

---

## 2. Severity Scale

| Severity | Meaning |
|----------|---------|
| Critical | Data loss, auth bypass, XSS, or complete loss of core user flow |
| High | Major workflow broken; no feedback on errors; destructive actions unconfirmed |
| Medium | Usability degraded; accessibility barrier; silent failures in edge cases |
| Low | Hygiene, polish, or defense-in-depth |

---

## 3. Audit Steps

### Step A — Read all frontend files

Read every file that touches the UI. For CueKeeper this was:

- `static/index.html`
- `static/style.css`
- `static/app.js`
- `src/main.py` (routes the frontend consumes: `/api/cues`, `/ws`, `/audio/*`, `/` static mount)
- `README.md` (feature claims vs reality)
- `tests/test_basic.py` (what's already covered)

### Step B — UX & accessibility audit

Check each of the following and record findings with file:line citations:

1. **Missing / mismatched features.** Does the README claim a feature (e.g. "GO button") that doesn't exist in markup or JS?
2. **Theme suitability.** Is a light theme usable in the intended environment (e.g. a darkened theater booth)? Is there a dark theme or `prefers-color-scheme` support?
3. **Labels on inputs.** Every `<input>` has an associated `<label>`; no placeholder-only labeling.
4. **Focus indicators.** `:focus-visible` outlines on all interactive elements; skip-to-content link present.
5. **Contrast.** Primary text ≥ 4.5:1 (AA), large text ≥ 3:1; status colors (red/green) meet contrast.
6. **ARIA.** Dynamic content (injected cue lists) uses `aria-live`; status indicators have `aria-label`/`role="status"`.
7. **Destructive actions.** Delete/destructive buttons require confirmation; are styled to be findable but not accidentally clickable.
8. **Feedback.** Upload/delete/play errors show user-visible messages (not just `console.error`).
9. **Empty states.** "No cues yet" or equivalent exists and is toggled correctly.
10. **Token flow.** If auth exists, is token entry a blocking `prompt()` or an inline UI field?

### Step C — Frontend code & client-side security audit

1. **XSS / injection.** Every user-controlled value rendered into `innerHTML`/`dataset` attributes is escaped. Check `escapeHtml`/`escapeAttr` coverage — are all fields covered?
2. **Attribute escaping.** `id`/`data-*` values in attributes are escaped (not just text content).
3. **Fetch error handling.** Every `fetch()` checks `r.ok`, handles 401/404/413/429/500, and has a `.catch()` with user-visible feedback.
4. **WebSocket client.** `JSON.parse` wrapped in `try/catch`; reconnect with exponential backoff (not fixed-interval infinite); `onerror` handler; token not exposed unnecessarily in URL.
5. **Audio / media.** `Audio()` src uses `encodeURIComponent`; playback errors surfaced to user; old audio cleaned up (`src=""`, `load()`) before new playback; no overlapping sounds unless intended.
6. **Token storage.** Token in `localStorage` — persisted but XSS-exposable; no way to view/edit stored token; consider inline field + `autocomplete="off"`.
7. **Event listeners.** Listeners not duplicated on re-render (e.g. `loadCues()` re-attaching handlers); cleanup on page unload.
8. **CSP / headers.** CSP meta tag or header present (`script-src 'self'` etc.); `Referrer-Policy` set; no `nonce`/`integrity` gaps if applicable.

### Step D — API contract vs frontend expectations

For each endpoint the frontend calls, verify:

| Endpoint | Frontend expects | Backend returns | Match? |
|----------|-----------------|-----------------|--------|
| `GET /api/cues` | `[{id,name,file}]` | JSON array | |
| `POST /api/cues` | 201 + `{id,name,file}` | | |
| `DELETE /api/cues/{id}` | 204 / 404 | | |
| `POST /api/cues/{id}/trigger` | broadcast `{action:"play",cue}` | | |
| `/audio/<file>` | playable audio URL | | |
| `/` | serves `index.html` | | |

Check for mismatches: frontend reads `r.json()` on a 429/500 error body → crash; upload error discards server `detail` message; local Play bypasses WebSocket broadcast (inconsistent GO semantics).

### Step E — Accessibility & UX findings

Record each finding as: ID / Severity / File:Line / Description / Impact / Recommendation.

### Step F — Produce report

Output a structured report:

```
# Frontend Audit Report — <Project>

## Summary Rating
Overall: <rating> — <one-line assessment>

## Critical / High findings
- ID — severity — file:line — description — impact — recommendation

## Medium / Low findings
(same format)

## Positive observations
- table of what's done well

## Recommended remediation priority
1. ...
2. ...
```



---

## 4. CueKeeper reference implementation

This skill was validated against CueKeeper (`/Users/elias/Developer/CueKeeper`). Key findings from that audit (use as reference patterns):

| ID | Severity | File | Finding |
|----|----------|------|---------|
| UX-01 | High | `static/index.html` | GO button styles exist (`.go` in CSS) but no markup in HTML — feature claimed in README but unimplemented |
| UX-02 | High | `static/style.css` | Light theme `#f5f5f5` unusable in darkened booth; no dark theme |
| UX-03 | High | `static/app.js` | Delete cue has no confirmation dialog |
| A11y-01 | Medium | `static/index.html` | No `<label>` on `cue-name`/`cue-file` inputs |
| A11y-02 | Medium | `static/style.css` | Upload msg red/green ≈3:1 contrast (fails WCAG AA) |
| C1 | High | `static/app.js:68–119` | `loadCues()` no status check, no `.catch()` — network error blanks cue list silently |
| C4 | Medium | `static/app.js:127` | `cue.file` interpolated raw into Audio URL without `encodeURIComponent()` |
| S2 | Low | `static/app.js:8–16` | Token in `localStorage` — XSS-exposable, no inline edit |

Remediation applied to CueKeeper: added GO button, inline token field, dark booth theme, labels/ARIA, WS reconnect with backoff, `encodeURIComponent`, delete confirmation, CSP, centralized error display, and 6 new security tests.

---

## 5. How to invoke

Run this skill manually by:

1. Reading all frontend files listed in Step A.
2. Working through Steps B–E, recording findings with file:line citations.
3. Producing the Step F report.
4. Prioritizing remediation (Critical/High first) and re-auditing after fixes.

**Verification:** After remediation, re-run the relevant test suite and manually smoke-test each user flow (upload, list, play, delete, GO, auth, reconnect).
