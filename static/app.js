const API = "/api/cues";
const AUDIO = "/audio";
let ws = null;
let currentAudio = null;

function wsStatus(connected) {
  const el = document.getElementById("ws-status");
  el.textContent = connected ? "Connected" : "Disconnected";
  el.className = connected ? "connected" : "disconnected";
}

function connectWs() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${protocol}//${window.location.host}/ws`;
  ws = new WebSocket(url);
  ws.onopen = () => wsStatus(true);
  ws.onclose = () => {
    wsStatus(false);
    setTimeout(connectWs, 1500);
  };
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.action === "play") {
      playCueByFile(msg.cue.file);
    }
  };
}

function loadCues() {
  fetch(API)
    .then((r) => r.json())
    .then((cues) => {
      const list = document.getElementById("cue-list");
      const noCues = document.getElementById("no-cues");
      list.innerHTML = "";
      if (cues.length === 0) {
        noCues.classList.remove("hidden");
        return;
      }
      noCues.classList.add("hidden");
      cues.forEach((cue) => {
        const el = document.createElement("div");
        el.className = "cue";
        el.innerHTML = `
          <div class="cue-info">
            <p class="cue-name">${escapeHtml(cue.name)}</p>
            <p class="cue-file">${escapeHtml(cue.file)}</p>
          </div>
          <div class="cue-actions">
            <button class="play" data-id="${cue.id}" data-file="${escapeAttr(cue.file)}">Play</button>
            <button class="delete" data-id="${cue.id}">Delete</button>
          </div>
        `;
        list.appendChild(el);
      });

      list.querySelectorAll("button.play").forEach((btn) => {
        btn.addEventListener("click", () => {
          playCueByFile(btn.dataset.file);
        });
      });

      list.querySelectorAll("button.delete").forEach((btn) => {
        btn.addEventListener("click", () => {
          const id = parseInt(btn.dataset.id, 10);
          fetch(`${API}/${id}`, { method: "DELETE" }).then(() => loadCues());
        });
      });
    });
}

function playCueByFile(file) {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  const audio = new Audio(`${AUDIO}/${file}`);
  currentAudio = audio;
  audio.play().catch((e) => console.error("Playback failed:", e));
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function escapeAttr(text) {
  return text.replace(/"/g, "&quot;");
}

document.getElementById("upload-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const name = document.getElementById("cue-name").value;
  const file = document.getElementById("cue-file").files[0];
  const msg = document.getElementById("upload-msg");
  const formData = new FormData();
  formData.append("name", name);
  formData.append("file", file);

  fetch(API, { method: "POST", body: formData })
    .then((r) => {
      if (!r.ok) throw new Error("Upload failed");
      return r.json();
    })
    .then(() => {
      document.getElementById("upload-form").reset();
      msg.textContent = "Uploaded.";
      msg.style.color = "green";
      loadCues();
    })
    .catch((err) => {
      msg.textContent = err.message;
      msg.style.color = "red";
    });
});

connectWs();
loadCues();
