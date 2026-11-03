// CueKeeper — frontend app
// All user-facing behavior: upload, list, play, delete, GO button,
// token handling, WebSocket resilience, dark/light theme, keyboard shortcuts,
// volume/audio controls, playback timer, and drag-to-reorder cue queue.

const API_BASE = ""; // same-origin
const STORAGE_KEY = "cuekeeper-theme";
const VOLUME_KEY = "cuekeeper-volume";
const MUTED_KEY = "cuekeeper-muted";
const TOKEN_KEY = "cuekeeper-token";

const els = {
  uploadForm: document.getElementById("upload-form"),
  cueName: document.getElementById("cue-name"),
  cueFile: document.getElementById("cue-file"),
  uploadBtn: document.getElementById("upload-btn"),
  uploadMsg: document.getElementById("upload-msg"),
  cueList: document.getElementById("cue-list"),
  noCues: document.getElementById("no-cues"),
  wsStatus: document.getElementById("ws-status"),
  goBtn: document.getElementById("go-btn"),
  themeToggle: document.getElementById("theme-toggle"),
  tokenInput: document.getElementById("cuekeeper-token"),
  tokenToggle: document.getElementById("token-toggle"),
  tokenSave: document.getElementById("token-save"),
  tokenMsg: document.getElementById("token-msg"),
  muteBtn: document.getElementById("mute-btn"),
  volumeSlider: document.getElementById("volume-slider"),
  timer: document.getElementById("timer"),
};

let accessToken = "";
let ws = null;
let wsReconnectTimer = null;
let audio = new Audio(); // shared audio element for cue playback
let playingCueId = null; // id of the cue currently playing
let selectedCueId = null; // id of the cue highlighted for keyboard nav
let uploadInFlight = false;
let volume = 1;
let muted = false;

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

function toggleTokenVisibility() {
  const input = els.tokenInput;
  if (input.type === "password") {
    input.type = "text";
    els.tokenToggle.textContent = "🙈";
    els.tokenToggle.setAttribute("aria-label", "Hide token");
  } else {
    input.type = "password";
    els.tokenToggle.textContent = "👁️";
    els.tokenToggle.setAttribute("aria-label", "Show token");
  }
}

function showTokenMsg(text, kind) {
  els.tokenMsg.textContent = text;
  els.tokenMsg.className = kind || "";
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

function loadSavedAudio() {
  try {
    const saved = localStorage.getItem(VOLUME_KEY);
    if (saved !== null) {
      volume = Math.min(Math.max(parseFloat(saved), 0), 1);
    }
    muted = localStorage.getItem(MUTED_KEY) === "true";
  } catch (e) {
    // ignore quota/private-mode errors
  }
  applyVolume();
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
  // Reconnect the WebSocket so it authenticates with the new token.
  connectWebSocket();
}

function setStatus(msg, connected) {
  els.wsStatus.textContent = msg;
  els.wsStatus.className = connected ? "connected" : "disconnected";
}

function htmlEscape(str) {
  return String(str).replace(/[&<>\"']/g, (c) => ({
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

function showUploadMsg(msg, kind) {
  els.uploadMsg.textContent = msg;
  els.uploadMsg.className = kind || "";
}

function setUploadLoading(loading) {
  uploadInFlight = loading;
  els.uploadBtn.disabled = loading;
  els.uploadBtn.textContent = loading ? "Uploading…" : "Upload";
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

async function uploadCue(evt) {
  evt.preventDefault();
  const name = els.cueName.value.trim();
  const file = els.cueFile.files[0];
  if (!name) {
    showUploadMsg("Enter a cue name", "error");
    return;
  }
  if (!file) {
    showUploadMsg("Choose an audio file", "error");
    return;
  }

  setUploadLoading(true);
  showUploadMsg("");
  const formData = new FormData();
  formData.append("name", name);
  formData.append("file", file);

  try {
    await api("/api/cues", { method: "POST", body: formData });
    els.cueName.value = "";
    els.cueFile.value = "";
    showUploadMsg("Cue uploaded", "success");
    loadCues();
  } catch (err) {
    showUploadMsg(err.message, "error");
  } finally {
    setUploadLoading(false);
  }
}

async function deleteCue(id) {
  if (!confirm("Delete this cue? This cannot be undone.")) {
    return;
  }
  try {
    await api("/api/cues/" + id, { method: "DELETE" });
    if (selectedCueId === id) selectedCueId = null;
    loadCues();
  } catch (err) {
    showUploadMsg(err.message, "error");
  }
}

async function reorderCues(order) {
  try {
    const cues = await api("/api/cues/reorder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order: order }),
    });
    renderCues(cues);
  } catch (err) {
    showUploadMsg("Reorder failed — " + err.message, "error");
    // Revert to server order.
    loadCues();
  }
}

/* ---------- Audio / volume ---------- */

function applyVolume() {
  audio.volume = muted ? 0 : volume;
  els.volumeSlider.value = Math.round(volume * 100);
  els.muteBtn.textContent = muted || volume === 0 ? "🔇" : "🔊";
  els.muteBtn.setAttribute("aria-label", muted ? "Unmute audio" : "Mute/unmute audio");
  try {
    localStorage.setItem(VOLUME_KEY, String(volume));
    localStorage.setItem(MUTED_KEY, String(muted));
  } catch (e) {
    // ignore
  }
}

function toggleMute() {
  muted = !muted;
  applyVolume();
}

function setVolumeFromSlider() {
  muted = false;
  volume = parseInt(els.volumeSlider.value, 10) / 100;
  applyVolume();
}

/* ---------- Playback ---------- */

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m + ":" + String(s).padStart(2, "0");
}

function updateTimer() {
  if (audio && audio.duration) {
    els.timer.textContent =
      formatTime(audio.currentTime) + " / " + formatTime(audio.duration);
  } else {
    els.timer.textContent = "0:00";
  }
}

function stopCurrent() {
  audio.pause();
  audio.src = "";
  audio.load();
  setPlayingCue(null);
  updateTimer();
}

function setPlayingCue(cueId) {
  playingCueId = cueId;
  document.querySelectorAll(".cue").forEach((el) => {
    el.classList.toggle("playing", el.dataset.cueId == cueId);
  });
  const playBtn = document.querySelector(`button.play[data-cue-id="${cueId}"]`);
  document.querySelectorAll("button.play").forEach((b) => {
    b.classList.toggle("playing", b === playBtn);
  });
}

async function playCue(file, cueId) {
  const url = "/audio/" + encodeURIComponent(file);
  stopCurrent();
  if (cueId != null) {
    setPlayingCue(cueId);
  }
  audio.src = url;
  try {
    await audio.play();
  } catch (err) {
    showUploadMsg("Could not play audio: " + err.message, "error");
    setPlayingCue(null);
    updateTimer();
    return;
  }
  audio.onended = () => {
    setPlayingCue(null);
    updateTimer();
  };
  audio.onerror = () => {
    setPlayingCue(null);
    updateTimer();
  };
  audio.ontimeupdate = updateTimer;
  updateTimer();
}

/* ---------- Cue list rendering ---------- */

function renderCues(cues) {
  const container = els.cueList;
  container.innerHTML = "";
  if (cues.length === 0) {
    els.noCues.hidden = false;
    selectedCueId = null;
    return;
  }
  els.noCues.hidden = true;
  for (const cue of cues) {
    const el = document.createElement("div");
    el.className = "cue";
    el.dataset.cueId = cue.id;
    el.draggable = true;
    el.dataset.index = cues.indexOf(cue);
    if (selectedCueId === cue.id) el.classList.add("selected");
    el.innerHTML = `
      <div class="drag-handle" aria-hidden="true">⠿</div>
      <div class="cue-info">
        <div class="cue-name">${htmlEscape(cue.name)}</div>
        <div class="cue-file">${htmlEscape(cue.file)}</div>
      </div>
      <div class="cue-actions">
        <button type="button" class="play" data-cue-id="${cue.id}" aria-label="Play ${htmlEscape(cue.name)}">Play</button>
        <button type="button" class="delete" data-cue-id="${cue.id}" aria-label="Delete ${htmlEscape(cue.name)}">Delete</button>
      </div>
    `;
    el.querySelector(".play").addEventListener("click", () => playCue(cue.file, cue.id));
    el.querySelector(".delete").addEventListener("click", () => deleteCue(cue.id));
    container.appendChild(el);
  }
}

function selectCue(cueId) {
  selectedCueId = cueId;
  document.querySelectorAll(".cue").forEach((el) => {
    el.classList.toggle("selected", el.dataset.cueId == cueId);
    if (el.dataset.cueId == cueId) el.scrollIntoView({ block: "nearest" });
  });
}

/* ---------- Drag-and-drop reordering ---------- */

let dragSourceId = null;

function setupDragDrop() {
  container = els.cueList;
  container.addEventListener("dragstart", (evt) => {
    const cue = evt.target.closest(".cue");
    if (!cue) return;
    dragSourceId = cue.dataset.cueId;
    cue.classList.add("dragging");
    evt.dataTransfer.effectAllowed = "move";
    evt.dataTransfer.setData("text/plain", dragSourceId);
  });
  container.addEventListener("dragend", (evt) => {
    const cue = evt.target.closest(".cue");
    if (cue) cue.classList.remove("dragging");
    dragSourceId = null;
  });
  container.addEventListener("dragover", (evt) => {
    evt.preventDefault();
    evt.dataTransfer.dropEffect = "move";
    const dragging = document.querySelector(".cue.dragging");
    if (!dragging) return;
    const afterElement = getDragAfterElement(container, evt.clientY);
    if (afterElement == null) {
      container.appendChild(dragging);
    } else {
      container.insertBefore(dragging, afterElement);
    }
  });
  container.addEventListener("drop", async (evt) => {
    evt.preventDefault();
    const id = evt.dataTransfer.getData("text/plain");
    if (!id || id === dragSourceId) {
      dragSourceId = null;
      return;
    }
    const order = Array.from(container.querySelectorAll(".cue")).map(
      (el) => parseInt(el.dataset.cueId, 10)
    );
    await reorderCues(order);
    dragSourceId = null;
  });
}

function getDragAfterElement(container, y) {
  const draggableElements = [
    ...container.querySelectorAll(".cue:not(.dragging)"),
  ];
  return draggableElements
    .reduce(
      (closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return { offset: offset, element: child };
        }
        return closest;
      },
      { offset: Number.NEGATIVE_INFINITY, element: null }
    ).element;
}

/* ---------- WebSocket ---------- */

let container; // set by setupDragDrop

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
        playCue(msg.cue.file, msg.cue.id);
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

/* ---------- Keyboard shortcuts ---------- */

function handleKeydown(evt) {
  const target = document.activeElement;
  const isInput =
    target.tagName === "INPUT" ||
    target.tagName === "TEXTAREA" ||
    target.isContentEditable;

  // Spacebar / Enter -> GO (play first cue) when not in an input.
  if ((evt.key === " " || evt.key === "Enter") && !isInput) {
    evt.preventDefault();
    els.goBtn.click();
    return;
  }

  if (!isInput && els.cueList.querySelector(".cue")) {
    const cues = Array.from(els.cueList.querySelectorAll(".cue"));
    const currentIndex = cues.findIndex(
      (el) => el.dataset.cueId == selectedCueId
    );
    let nextIndex = currentIndex;
    if (evt.key === "ArrowDown") {
      evt.preventDefault();
      nextIndex = Math.min(currentIndex + 1, cues.length - 1);
    } else if (evt.key === "ArrowUp") {
      evt.preventDefault();
      nextIndex = Math.max(currentIndex - 1, 0);
    }
    if (nextIndex !== currentIndex) {
      selectCue(cues[nextIndex].dataset.cueId);
    }
  }
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
els.tokenToggle.addEventListener("click", toggleTokenVisibility);
els.muteBtn.addEventListener("click", toggleMute);
els.volumeSlider.addEventListener("input", setVolumeFromSlider);

window.addEventListener("keydown", handleKeydown);

applyTheme(localStorage.getItem(STORAGE_KEY) || null);
loadSavedAudio();
connectWebSocket();
loadCues();
setupDragDrop();
