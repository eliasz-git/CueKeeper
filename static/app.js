// CueKeeper — frontend app
// All user-facing behavior: upload, list, play, delete, GO button,
// token handling, WebSocket resilience, dark/light theme.

const API_BASE = ""; // same-origin
const STORAGE_KEY = "cuekeeper-theme";
const TOKEN_KEY = "cuekeeper-token";

const els = {
  uploadForm: document.getElementById("upload-form"),
  cueName: document.getElementById("cue-name"),
  cueFile: document.getElementById("cue-file"),
  uploadMsg: document.getElementById("upload-msg"),
  cueList: document.getElementById("cue-list"),
  noCues: document.getElementById("no-cues"),
  wsStatus: document.getElementById("ws-status"),
  goBtn: document.getElementById("go-btn"),
  themeToggle: document.getElementById("theme-toggle"),
  tokenInput: document.getElementById("cuekeeper-token"),
  tokenSave: document.getElementById("token-save"),
  tokenMsg: document.getElementById("token-msg"),
};

let accessToken = "";
let ws = null;
let wsReconnectTimer = null;
let audio = new Audio(); // shared audio element for cue playback

function applyTheme(saved) {
  if (saved === "light") {
    document.documentElement.setAttribute("data-theme", "light");
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
  updateThemeButton();
}

function updateThemeButton() {
  const dark = !document.documentElement.hasAttribute("data-theme");
  els.themeToggle.textContent = dark ? "Light theme" : "Dark theme";
}

function toggleTheme() {
  const next = document.documentElement.hasAttribute("data-theme")
    ? null
    : "light";
  localStorage.setItem(STORAGE_KEY, next || "");
  applyTheme(next);
}

function showTokenMsg(text, kind) {
  els.tokenMsg.textContent = text;
  els.tokenMsg.className = kind;
}

function loadSavedToken() {
  try {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (saved) {
      accessToken = saved;
      els.tokenInput.value = saved;
    }
  } catch (e) {
    // localStorage may be unavailable in private mode — ignore.
  }
}

function saveToken() {
  const val = els.tokenInput.value.trim();
  if (!val) {
    showTokenMsg("Enter a token", "error");
    return;
  }
  accessToken = val;
  try {
    localStorage.setItem(TOKEN_KEY, val);
  } catch (e) {
    // ignore quota/private-mode errors
  }
  showTokenMsg("Token saved", "success");
}

function setStatus(msg, connected) {
  els.wsStatus.textContent = msg;
  els.wsStatus.className = connected ? "connected" : "disconnected";
}

function htmlEscape(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

function authHeaders() {
  const h = {};
  if (accessToken) {
    h["Authorization"] = "Bearer " + accessToken;
  }
  return h;
}

async function api(path, opts = {}) {
  const res = await fetch(API_BASE + path, {
    headers: { ...authHeaders(), ...opts.headers },
    ...opts,
  });
  if (res.status === 401) {
    throw new Error("Unauthorized — check your access token.");
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error("Request failed (" + res.status + "): " + (body || res.statusText));
  }
  if (res.status === 204) return null;
  return res.json();
}

async function loadCues() {
  try {
    const cues = await api("/api/cues");
    renderCues(cues);
  } catch (err) {
    showUploadMsg(err.message, "error");
    setStatus("Error — " + err.message, false);
  }
}

async function uploadCue(e) {
  e.preventDefault();
  const formData = new FormData();
  formData.append("name", els.cueName.value.trim());
  formData.append("file", els.cueFile.files[0]);

  try {
    await api("/api/cues", { method: "POST", body: formData });
    els.uploadForm.reset();
    showUploadMsg("Cue uploaded", "success");
    loadCues();
  } catch (err) {
    showUploadMsg(err.message, "error");
  }
}

async function deleteCue(id) {
  if (!confirm("Delete this cue?")) return;
  try {
    await api("/api/cues/" + id, { method: "DELETE" });
    loadCues();
  } catch (err) {
    showUploadMsg(err.message, "error");
  }
}

function stopCurrent() {
  audio.pause();
  audio.src = "";
  audio.load();
}

async function playCue(file) {
  const url = "/audio/" + encodeURIComponent(file);
  stopCurrent();
  audio.src = url;
  try {
    await audio.play();
  } catch (err) {
    showUploadMsg("Could not play audio: " + err.message, "error");
  }
}

function showUploadMsg(msg, kind) {
  els.uploadMsg.textContent = msg;
  els.uploadMsg.className = kind;
}

function renderCues(cues) {
  const container = els.cueList;
  container.innerHTML = "";
  if (cues.length === 0) {
    els.noCues.hidden = false;
    return;
  }
  els.noCues.hidden = true;
  for (const cue of cues) {
    const el = document.createElement("div");
    el.className = "cue";
    el.innerHTML = `
      <div class="cue-info">
        <div class="cue-name">${htmlEscape(cue.name)}</div>
        <div class="cue-file">${htmlEscape(cue.file)}</div>
      </div>
      <div class="cue-actions">
        <button type="button" class="play" data-id="${cue.id}" aria-label="Play ${htmlEscape(cue.name)}">Play</button>
        <button type="button" class="delete" data-id="${cue.id}" aria-label="Delete ${htmlEscape(cue.name)}">Delete</button>
      </div>
    `;
    el.querySelector(".play").addEventListener("click", () => playCue(cue.file));
    el.querySelector(".delete").addEventListener("click", () => deleteCue(cue.id));
    container.appendChild(el);
  }
}

function connectWebSocket() {
  if (ws) {
    ws.close();
  }

  const scheme = location.protocol === "https:" ? "wss:" : "ws:";
  let url = scheme + "//" + location.host + "/ws";
  if (accessToken) {
    url += "?token=" + encodeURIComponent(accessToken);
  }

  ws = new WebSocket(url);

  ws.onopen = () => {
    setStatus("Connected", true);
    if (wsReconnectTimer) {
      clearTimeout(wsReconnectTimer);
      wsReconnectTimer = null;
    }
  };

  ws.onclose = () => {
    setStatus("Disconnected — reconnecting…", false);
    scheduleReconnect();
  };

  ws.onerror = () => {
    setStatus("Connection error", false);
    ws.close();
  };

  ws.onmessage = (evt) => {
    try {
      const msg = JSON.parse(evt.data);
      if (msg.action === "play" && msg.cue && msg.cue.file) {
        playCue(msg.cue.file);
      }
    } catch (e) {
      // ignore malformed messages
    }
  };
}

function scheduleReconnect() {
  if (wsReconnectTimer) return;
  let delay = 1000;
  const attempt = () => {
    wsReconnectTimer = null;
    connectWebSocket();
    delay = Math.min(delay * 2, 30000);
  };
  wsReconnectTimer = setTimeout(attempt, delay);
}

els.uploadForm.addEventListener("submit", uploadCue);
els.goBtn.addEventListener("click", () => {
  const firstPlay = els.cueList.querySelector(".play");
  if (firstPlay) {
    stopCurrent();
    firstPlay.click();
  } else {
    showUploadMsg("No cues to play", "error");
  }
});

els.themeToggle.addEventListener("click", toggleTheme);
els.tokenSave.addEventListener("click", saveToken);

applyTheme(localStorage.getItem(STORAGE_KEY) || null);
loadSavedToken();
connectWebSocket();
loadCues();
