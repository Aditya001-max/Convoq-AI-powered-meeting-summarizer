/**
 * Convoq — Offscreen Document
 * Runs MediaRecorder on the captured tab audio stream.
 * Offscreen docs have access to Web APIs that service workers lack.
 */

let mediaRecorder = null;
let chunkInterval  = null;
let audioChunks    = [];
let mimeType       = "audio/webm;codecs=opus";

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "START_CAPTURE") startCapture(msg.streamId, msg.chunkMs);
  if (msg.type === "STOP_CAPTURE")  stopCapture();
});

async function startCapture(streamId, chunkMs) {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource:   "tab",
          chromeMediaSourceId: streamId,
        },
      },
      video: false,
    });

    // Pick best supported format
    if (!MediaRecorder.isTypeSupported(mimeType)) {
      mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/ogg";
    }

    mediaRecorder = new MediaRecorder(stream, { mimeType });
    audioChunks   = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    // Every chunkMs, flush current audio to background for transcription
    chunkInterval = setInterval(async () => {
      if (!audioChunks.length) return;

      mediaRecorder.requestData();
      await new Promise(r => setTimeout(r, 200)); // let ondataavailable fire

      const blob     = new Blob(audioChunks, { type: mimeType });
      const base64   = await blobToBase64(blob);
      audioChunks    = [];

      chrome.runtime.sendMessage({
        type:        "AUDIO_CHUNK",
        audioBase64: base64,
        mimeType,
      });
    }, chunkMs);

    mediaRecorder.start(1000); // collect in 1s slices

  } catch (err) {
    console.error("[Convoq Offscreen] Capture error:", err);
  }
}

function stopCapture() {
  clearInterval(chunkInterval);
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
  }
  mediaRecorder = null;
  audioChunks   = [];
}

function blobToBase64(blob) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(",")[1]);
    reader.readAsDataURL(blob);
  });
}
