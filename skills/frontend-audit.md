# Skill: Frontend Audit

Purpose: A reusable, structured skill for auditing everything facing the user in a web application **or native/cross-platform app** — HTML/CSS/JS, native UI, accessibility, UX, client-side security, performance, installation, permissions, and error handling.

Use this skill when you need to review a user-facing surface before release, after a UI change, or as part of a security/UX audit. It covers web apps, native mobile/desktop apps, and hybrid/cross-platform apps (React Native, Flutter, Electron, Tauri, Godot, Unity, etc.).

---

## 0. Identify the app type

Before auditing, classify the frontend so you know which sections apply:

| Type | Examples | Applies |
|------|----------|---------|
| Web app / website | CueKeeper static UI, React SPA, Next.js | All web sections + installation section (PWA, direct URL) |
| Native mobile | Swift (iOS), Kotlin (Android), Objective-C | Native mobile + installation (app stores, sideloading) |
| Native desktop | Swift (macOS), .NET (WinUI), GTK/Qt (Linux) | Native desktop + installation |
| Cross-platform | React Native, Flutter, .NET MAUI | Native mobile/desktop + JS bridge sections |
| Hybrid / webview | Electron, Tauri, Capacitor, Cordova | Web sections + native container sections |
| Game engine | Godot, Unity, Unreal | Native sections + game-specific (HUD, input, scenes) |

---

## 1. Severity Scale

| Severity | Meaning |
|----------|---------|
| Critical | Data loss, auth bypass, XSS/injection, complete loss of core user flow, crash-on-launch |
| High | Major workflow broken; no feedback on errors; destructive actions unconfirmed; permissions abused |
| Medium | Usability degraded; accessibility barrier; silent failures; silent permission grants |
| Low | Hygiene, polish, defense-in-depth |

---

## 2. Universal audit steps (all frontend types)

### Step A — Read all user-facing files

For each layer, read the files that shape what the user sees and touches:

- **Web:** `index.html`, `style.css`, `app.js`, route handlers (`/`, `/api/*`, `/ws`), static mounts, CSP headers.
- **Native mobile:** `MainActivity.kt`/`AppDelegate.swift`, layout XML (`res/layout/`), SwiftUI/UIView files, `AndroidManifest.xml`, `Info.plist`.
- **Cross-platform:** `pubspec.yaml` + `lib/` (Flutter), `App.tsx` + `src/` (React Native), `*.xaml` (MAUI).
- **Desktop/electron:** `main.js`, `preload.js`, `renderer.js`, `package.json`, `index.html`.
- **Game engine:** `.tscn`/`.gd` (Godot), scenes, HUD/canvas, input maps.
- **Docs:** `README.md`, feature claims vs reality, quick-start.
- **Tests:** UI/E2E test suites covering user flows.

### Step B — UX & accessibility audit (universal)

Check each item and record findings with file:line or screen citations:

1. **Missing/mismatched features.** Does documentation claim a feature that doesn't exist in UI?
2. **Theme suitability.** Is the default theme appropriate for the environment (e.g. dark booth, bright outdoors)? Dark theme, `prefers-color-scheme`, or native dark mode support?
3. **Labels.** Every input has an associated label; no placeholder-only labeling.
4. **Focus / keyboard navigation.** Visible focus indicators; logical tab order; no keyboard traps; skip-to-content (web) or equivalent.
5. **Contrast.** Text ≥ 4.5:1 (AA), large text ≥ 3:1; status colors meet contrast on both light and dark themes.
6. **Touch targets.** Minimum 44×44 dp (iOS) / 48×48 dp (Android) for tappable controls; sufficient spacing.
7. **Screen readers.** Dynamic content announced (`aria-live` web; `UIAccessibility` iOS; `contentDescription` Android; `Semantics` Flutter); custom controls expose roles/values.
8. **Destructive actions.** Delete/logout/reset require confirmation; styled to be findable but hard to tap accidentally.
9. **Feedback.** Upload/delete/play/save errors show user-visible messages (toast, snackbar, dialog, inline error) — not just logs/console.
10. **Empty states.** "No data" or equivalent exists and renders correctly.
11. **Token / credential flow.** If auth exists, is entry a blocking system dialog or inline UI field? Are secrets stored securely (Keychain/Keystore, not plain localStorage)?
12. **Localization.** Strings externalized; RTL layout support; date/number/currency formatting locale-aware.
13. **Motion / vestibular.** Animations can be reduced (`prefers-reduced-motion`; native accessibility settings); no auto-playing motion that can't be paused.

### Step C — Frontend code & client-side security (universal)

1. **Injection / XSS.** Every user-controlled value rendered into innerHTML/templates/native text views is escaped or bound safely. Check custom-rendered lists, chat messages, filenames, cue names.
2. **Attribute escaping.** `id`/`data-*`/native attributes escaped, not just text content.
3. **Network error handling.** Every API call checks status codes, handles 401/404/413/429/500, and has error boundaries with user-visible feedback.
4. **Realtime / WebSocket.** `JSON.parse` wrapped in try/catch; reconnect with exponential backoff (not fixed-interval infinite); `onerror`; token not unnecessarily exposed in URLs/logs.
5. **Audio / media.** URLs use `encodeURIComponent`; playback errors surfaced to user; old media cleaned up before new playback; no overlapping unless intended; respects mute/silent switches.
6. **Token / secret storage.** Secrets in Keychain (iOS), EncryptedSharedPreferences/Keystore (Android), or secure enclave — not plain `localStorage`, `UserDefaults`, `SharedPreferences`, or source code. No hardcoded keys/secrets.
7. **Event listeners / listeners.** Not duplicated on re-render; removed on dispose/unmount/page unload.
8. **CSP / transport security.** Web: CSP meta/header (`script-src 'self'`); `Referrer-Policy`; SRI if CDN. Native: ATS (iOS) / cleartext traffic policy (Android); no `allowAllTraffic` unless justified; certificate pinning where sensitive.
9. **Permissions.** Only requested permissions that are used; rationale strings provided; graceful degradation when denied; no silent background location/mic/camera use.
10. **Local data safety.** Local DB/files (`data.json`, SQLite, localStorage) written atomically (tmp+replace or transaction); corruption recovery; no plaintext secrets on disk.

### Step D — Platform-specific sections

#### Web (HTML/CSS/JS)
- Semantic HTML (`<header>`, `<main>`, `<section>`, `<footer>`, `<label>`, `<button type="button">`).
- CSP meta tag or header; `X-Content-Type-Options: nosniff`; `X-Frame-Options: DENY`.
- Viewport meta tag; responsive breakpoints; mobile touch targets.
- `encodeURIComponent` on dynamic URLs; `audio.play()` errors caught and shown.
- Service worker / PWA installability (if applicable).

#### Native mobile (iOS / Android)
- `Info.plist` / `AndroidManifest.xml` permission declarations with usage descriptions.
- Biometric authentication (Face ID / fingerprint) for sensitive actions if applicable.
- Keychain / EncryptedSharedPreferences for tokens.
- App store metadata accuracy (screenshots match actual UI).
- Crash on launch / cold start time; ANR (Android) / watchdog (iOS).
- Background mode appropriateness (audio, location, VoIP).

#### Desktop (macOS / Windows / Linux)
- Code signing / notarization (macOS); Windows Authenticode.
- Auto-update mechanism (Sparkle, Windows Update, app store).
- Window management (resizable, accessible title bar, keyboard shortcuts).
- Tray / menu bar behavior (if applicable).
- File associations and default-app handling.

#### Hybrid / webview (Electron / Tauri / Capacitor)
- `nodeIntegration` / context isolation (Electron); Tauri allowlist.
- Preload script exposes only necessary APIs.
- CSP strict for webview content.
- Native dialogs vs web dialogs consistency.

#### Game engine (Godot / Unity)
- HUD/CanvasLayer readability; font sizes; color-blind-safe palettes.
- Input mapping (keyboard/gamepad/touch); remappable controls.
- Scene transitions and loading states.
- Audio bus layout; SFX/music/mute sliders.
- Accessibility: screen reader support varies — document limitations.

### Step E — Installation & distribution audit (apps)

1. **Install path.** App store vs sideload vs direct download vs `pip`/`npm`/`brew` vs source. Is the path documented?
2. **First-run experience.** Does the app work on first launch without config? Are required env vars/credentials clear?
3. **Updates.** Auto-update notified? Manual download required? Version visible in UI (About / settings)?
4. **Uninstall / data cleanup.** Does removing the app delete local data? Is there an export/backup path?
5. **Code signing.** Is the binary signed? Are unsigned builds distributed?

---

## 3. CueKeeper reference implementation

This skill was validated against CueKeeper (`/Users/elias/Developer/CueKeeper`), a FastAPI + vanilla JS theater sound-cue manager.

| ID | Severity | File | Finding |
|----|----------|------|---------|
| UX-01 | High | `static/index.html` | GO button styles exist (`.go` CSS) but no HTML markup — feature claimed in README but unimplemented |
| UX-02 | High | `static/style.css` | Light theme `#f5f5f5` unusable in darkened booth; no dark theme |
| UX-03 | High | `static/app.js` | Delete cue has no confirmation dialog |
| A11y-01 | Medium | `static/index.html` | No `<label>` on `cue-name`/`cue-file` inputs |
| A11y-02 | Medium | `static/style.css` | Upload status red/green ≈3:1 contrast (fails WCAG AA) |
| C1 | High | `static/app.js:68–119` | `loadCues()` no status check, no `.catch()` — network error blanks cue list silently |
| C4 | Medium | `static/app.js:127` | `cue.file` interpolated raw into Audio URL without `encodeURIComponent()` |
| S2 | Low | `static/app.js:8–16` | Token in `localStorage` — XSS-exposable, no inline edit |

**Remediation applied:** added GO button, inline token field, dark booth theme, labels/ARIA, WS reconnect with backoff, `encodeURIComponent`, delete confirmation, CSP, centralized error display, and 6 new security tests (37 passing).

---

## 4. How to invoke

Run this skill manually by:

1. **Classify** the frontend type (Section 0).
2. **Read** all user-facing files (Step A).
3. **Work through** Steps B–E, recording findings with file:line or screen citations.
4. **Produce** a structured report (summary rating, Critical/High findings, Medium/Low findings, positives, remediation priority).
5. **Re-audit** after remediation; re-run test suite and smoke-test each user flow (upload, list, play, delete, GO, auth, reconnect, install, first launch).

**Verification:** After fixes, confirm no Critical/High findings remain and user-facing tests pass.
