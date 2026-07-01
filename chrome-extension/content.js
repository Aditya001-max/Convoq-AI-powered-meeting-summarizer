/**
 * Convoq — Content Script (injected into meet.google.com)
 * Injects the floating recording widget into the Google Meet page.
 */

(function () {
  if (document.getElementById("convoq-widget")) return;

  // ── Build widget ──────────────────────────────────────────────────────

  const widget = document.createElement("div");
  widget.id = "convoq-widget";
  widget.innerHTML = `
    <div id="cq-header">
      <div id="cq-logo">
        <svg width="18" height="18" viewBox="0 0 22 22" fill="none">
          <rect width="22" height="22" rx="6" fill="#C2410C"/>
          <path d="M6 8h10M6 11h7M6 14h5" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
        <span>Convoq</span>
      </div>
      <button id="cq-minimise" title="Minimise">−</button>
    </div>

    <div id="cq-body">
      <div id="cq-status">
        <span id="cq-dot"></span>
        <span id="cq-status-text">Ready to record</span>
      </div>

      <div id="cq-transcript-box">
        <p id="cq-transcript-placeholder">Live transcript will appear here…</p>
      </div>

      <div id="cq-chunks-count" style="display:none">
        <span id="cq-chunks-num">0</span> chunk(s) transcribed
      </div>

      <div id="cq-actions">
        <button id="cq-start"   class="cq-btn cq-btn-primary">Start Recording</button>
        <button id="cq-stop"    class="cq-btn cq-btn-secondary" style="display:none">Pause</button>
        <button id="cq-finalise"class="cq-btn cq-btn-accent"   style="display:none">End &amp; Summarise →</button>
      </div>

      <div id="cq-title-row" style="display:none">
        <input id="cq-title" type="text" placeholder="Meeting title (optional)" autocomplete="off"/>
      </div>
    </div>
  `;

  document.body.appendChild(widget);

  // ── State ─────────────────────────────────────────────────────────────

  let recording  = false;
  let minimised  = false;
  let transcript = [];

  const dot        = widget.querySelector("#cq-dot");
  const statusText = widget.querySelector("#cq-status-text");
  const txBox      = widget.querySelector("#cq-transcript-box");
  const txPlaceh   = widget.querySelector("#cq-transcript-placeholder");
  const chunksEl   = widget.querySelector("#cq-chunks-count");
  const chunksNum  = widget.querySelector("#cq-chunks-num");
  const startBtn   = widget.querySelector("#cq-start");
  const stopBtn    = widget.querySelector("#cq-stop");
  const finalBtn   = widget.querySelector("#cq-finalise");
  const titleRow   = widget.querySelector("#cq-title-row");
  const titleInput = widget.querySelector("#cq-title");
  const minBtn     = widget.querySelector("#cq-minimise");
  const body       = widget.querySelector("#cq-body");

  // ── Helpers ───────────────────────────────────────────────────────────

  function setStatus(text, isRec) {
    statusText.textContent = text;
    dot.className = isRec ? "cq-dot-rec" : "cq-dot-idle";
  }

  function appendTranscript(text) {
    txPlaceh.style.display = "none";
    const p = document.createElement("p");
    p.textContent = text;
    txBox.appendChild(p);
    txBox.scrollTop = txBox.scrollHeight;
  }

  // ── Button handlers ───────────────────────────────────────────────────

  startBtn.addEventListener("click", () => {
    const title = getMeetTitle();
    chrome.runtime.sendMessage(
      { type: "START_RECORDING", tabId: null, title },
      (res) => {
        if (res && res.ok) {
          recording = true;
          setStatus("Recording…", true);
          startBtn.style.display  = "none";
          stopBtn.style.display   = "inline-block";
          finalBtn.style.display  = "inline-block";
          titleRow.style.display  = "none";
          chunksEl.style.display  = "block";
        } else {
          setStatus("Error — see popup", false);
        }
      }
    );
  });

  stopBtn.addEventListener("click", () => {
    if (recording) {
      chrome.runtime.sendMessage({ type: "STOP_RECORDING" }, () => {
        recording = false;
        setStatus("Paused", false);
        stopBtn.textContent = "Resume";
        stopBtn.onclick = resumeRecording;
      });
    }
  });

  function resumeRecording() {
    const title = getMeetTitle();
    chrome.runtime.sendMessage(
      { type: "START_RECORDING", tabId: null, title },
      (res) => {
        if (res && res.ok) {
          recording = true;
          setStatus("Recording…", true);
          stopBtn.textContent = "Pause";
          stopBtn.onclick = null;
          stopBtn.addEventListener("click", () => {});
        }
      }
    );
  }

  finalBtn.addEventListener("click", () => {
    setStatus("Processing…", false);
    startBtn.style.display  = "none";
    stopBtn.style.display   = "none";
    finalBtn.style.display  = "none";
    chrome.runtime.sendMessage({ type: "FINALISE" }, () => {
      setStatus("Done — opening Convoq ↗", false);
    });
  });

  minBtn.addEventListener("click", () => {
    minimised = !minimised;
    body.style.display  = minimised ? "none" : "block";
    minBtn.textContent  = minimised ? "+" : "−";
    widget.style.width  = minimised ? "auto" : "";
  });

  // ── Receive transcript updates ────────────────────────────────────────

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "TRANSCRIPT_UPDATE") {
      appendTranscript(msg.latest);
      chunksNum.textContent = msg.total;
    }
  });

  // ── Utility ───────────────────────────────────────────────────────────

  function getMeetTitle() {
    if (titleInput.value.trim()) return titleInput.value.trim();
    // Try to grab the meeting title from the Meet page DOM
    const el = document.querySelector('[data-meeting-title]')
            || document.querySelector('h1')
            || document.title;
    return typeof el === "string" ? el : (el?.textContent?.trim() || "Google Meet");
  }

  // Show title input before recording starts
  titleRow.style.display = "block";

})();
