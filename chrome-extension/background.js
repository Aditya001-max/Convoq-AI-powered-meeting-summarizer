/**
 * Convoq for Google Meet — Background Service Worker
 * Handles tab audio capture, chunk transcription, and session management.
 */

const CONVOQ_BASE = "https://convoq-ai-powered-meeting-summarize.vercel.app";
const CHUNK_MS    = 30_000; // 30-second transcription chunks

let state = {
  recording:   false,
  tabId:       null,
  sessionTitle: "",
  chunks:      [],      // accumulated transcription strings
  startTime:   null,
};

// ── Offscreen document management ────────────────────────────────────────

async function ensureOffscreen() {
  const existing = await chrome.offscreen.hasDocument().catch(() => false);
  if (!existing) {
    await chrome.offscreen.createDocument({
      url:    "offscreen.html",
      reasons: ["USER_MEDIA"],
      justification: "Capture tab audio for meeting transcription",
    });
  }
}

async function closeOffscreen() {
  const existing = await chrome.offscreen.hasDocument().catch(() => false);
  if (existing) await chrome.offscreen.closeDocument();
}

// ── Start recording ───────────────────────────────────────────────────────

async function startRecording(tabId, title) {
  if (state.recording) return { ok: false, error: "Already recording" };

  try {
    // Capture the tab's audio stream
    const streamId = await new Promise((resolve, reject) => {
      chrome.tabCapture.getMediaStreamId({ targetTabId: tabId }, id => {
        if (chrome.runtime.lastError) reject(chrome.runtime.lastError);
        else resolve(id);
      });
    });

    state = {
      recording:   true,
      tabId,
      sessionTitle: title || "Google Meet Recording",
      chunks:      [],
      startTime:   Date.now(),
    };

    await chrome.storage.session.set({ convoqState: state });

    await ensureOffscreen();
    chrome.runtime.sendMessage({ type: "START_CAPTURE", streamId, chunkMs: CHUNK_MS });

    return { ok: true };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

// ── Stop recording + finalise ─────────────────────────────────────────────

async function stopRecording(submit = false) {
  if (!state.recording) return { ok: false, error: "Not recording" };

  chrome.runtime.sendMessage({ type: "STOP_CAPTURE" });
  await closeOffscreen();

  const duration = Math.round((Date.now() - state.startTime) / 60000);
  const fullTranscript = state.chunks.join("\n\n");

  state.recording = false;
  await chrome.storage.session.set({ convoqState: state });

  if (submit && fullTranscript.trim()) {
    await submitToConvoq(fullTranscript, state.sessionTitle, duration);
  }

  return { ok: true, transcript: fullTranscript };
}

// ── Submit transcript to Convoq ───────────────────────────────────────────

async function submitToConvoq(transcript, title, durationMinutes) {
  const body = new URLSearchParams({
    transcript_text:  transcript,
    meeting_type:     "general",
    meeting_title:    title,
    duration_minutes: durationMinutes,
  });

  try {
    const res = await fetch(`${CONVOQ_BASE}/process`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });

    if (res.ok && res.redirected) {
      // Open the results page in a new tab
      chrome.tabs.create({ url: res.url });
    } else if (res.ok) {
      chrome.tabs.create({ url: `${CONVOQ_BASE}/history` });
    }
  } catch (err) {
    console.error("[Convoq] Submit error:", err);
  }
}

// ── Send audio chunk to Whisper transcription ─────────────────────────────

async function transcribeChunk(audioBase64, mimeType) {
  try {
    const blob = base64ToBlob(audioBase64, mimeType);
    const formData = new FormData();
    formData.append("audio", blob, "chunk.webm");

    const res = await fetch(`${CONVOQ_BASE}/api/transcribe-chunk`, {
      method: "POST",
      body:   formData,
    });

    if (res.ok) {
      const data = await res.json();
      const text = (data.transcript || "").trim();
      if (text) {
        state.chunks.push(text);
        await chrome.storage.session.set({ convoqState: state });
        // Notify content script with the latest text
        if (state.tabId) {
          chrome.tabs.sendMessage(state.tabId, {
            type:   "TRANSCRIPT_UPDATE",
            latest: text,
            total:  state.chunks.length,
          }).catch(() => {});
        }
      }
    }
  } catch (err) {
    console.error("[Convoq] Transcription error:", err);
  }
}

function base64ToBlob(base64, mimeType) {
  const byteChars = atob(base64);
  const arr = new Uint8Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) arr[i] = byteChars.charCodeAt(i);
  return new Blob([arr], { type: mimeType });
}

// ── Message listener ──────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  switch (msg.type) {

    case "START_RECORDING":
      startRecording(msg.tabId || _sender.tab?.id, msg.title).then(sendResponse);
      return true;

    case "STOP_RECORDING":
      stopRecording(false).then(sendResponse);
      return true;

    case "FINALISE":
      stopRecording(true).then(sendResponse);
      return true;

    case "OPEN_POPUP":
      chrome.action.openPopup().catch(() => {});
      break;

    case "GET_STATE":
      sendResponse({ state });
      break;

    case "AUDIO_CHUNK":
      transcribeChunk(msg.audioBase64, msg.mimeType);
      break;
  }
});

// Restore state on service worker restart
chrome.storage.session.get("convoqState", ({ convoqState }) => {
  if (convoqState) state = convoqState;
});
