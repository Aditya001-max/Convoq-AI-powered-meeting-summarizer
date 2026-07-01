/**
 * Convoq Popup — communicates with background service worker.
 */

const dot        = document.getElementById("dot");
const statusLbl  = document.getElementById("status-label");
const chunksLine = document.getElementById("chunks-line");
const startBtn   = document.getElementById("btn-start");
const stopBtn    = document.getElementById("btn-stop");
const finalBtn   = document.getElementById("btn-finalise");
const notMeet    = document.getElementById("not-meet-msg");

// ── Helpers ───────────────────────────────────────────────────────────────

function setStatus(text, isRec) {
  statusLbl.textContent = text;
  dot.className = isRec ? "dot-rec" : "dot-idle";
}

function setChunks(n) {
  chunksLine.textContent = n > 0 ? `${n} chunk(s) transcribed` : "No transcription yet";
}

function showButtons(recording) {
  startBtn.style.display  = recording ? "none"         : "flex";
  stopBtn.style.display   = recording ? "flex"         : "none";
  finalBtn.style.display  = recording ? "flex"         : "none";
}

// ── Check if we're on Google Meet ─────────────────────────────────────────

async function checkTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const isMeet = tab?.url?.includes("meet.google.com") && tab.url.includes("/") &&
                 !tab.url.endsWith("meet.google.com/");
  notMeet.style.display = isMeet ? "none" : "block";
  return isMeet ? tab : null;
}

// ── Sync state from background ────────────────────────────────────────────

function syncState() {
  chrome.runtime.sendMessage({ type: "GET_STATE" }, (res) => {
    if (!res) return;
    const { state } = res;
    setStatus(state.recording ? "Recording…" : "Idle", state.recording);
    setChunks(state.chunks?.length || 0);
    showButtons(state.recording);
  });
}

// ── Button handlers ───────────────────────────────────────────────────────

startBtn.addEventListener("click", async () => {
  const tab = await checkTab();
  if (!tab) return;

  chrome.runtime.sendMessage(
    { type: "START_RECORDING", tabId: tab.id, title: tab.title },
    (res) => {
      if (res?.ok) {
        setStatus("Recording…", true);
        showButtons(true);
      } else {
        setStatus("Error: " + (res?.error || "unknown"), false);
      }
    }
  );
});

stopBtn.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "STOP_RECORDING" }, () => {
    setStatus("Paused", false);
    stopBtn.textContent = "▶ Resume";
    stopBtn.onclick = async () => {
      const tab = await checkTab();
      chrome.runtime.sendMessage({ type: "START_RECORDING", tabId: tab?.id, title: "" }, syncState);
    };
  });
});

finalBtn.addEventListener("click", () => {
  setStatus("Processing…", false);
  startBtn.style.display  = "none";
  stopBtn.style.display   = "none";
  finalBtn.style.display  = "none";
  chrome.runtime.sendMessage({ type: "FINALISE" }, () => {
    setStatus("Done — Convoq opened ↗", false);
    chunksLine.textContent = "Summary ready in Convoq";
  });
});

// ── Init ──────────────────────────────────────────────────────────────────

checkTab();
syncState();

// Refresh state while popup is open
setInterval(syncState, 3000);
