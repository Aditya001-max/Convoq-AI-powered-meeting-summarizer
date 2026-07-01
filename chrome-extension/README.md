# Convoq Chrome Extension

Records Google Meet calls and sends them to your local Convoq instance for AI summarisation.

## Install (developer mode)

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked**
4. Select this `chrome-extension/` folder

## Icons (required before loading)

Place three PNG icon files in `chrome-extension/icons/`:

| File | Size |
|---|---|
| `icon16.png` | 16×16 |
| `icon48.png` | 48×48 |
| `icon128.png` | 128×128 |

You can use any simple logo. A square orange (`#C2410C`) image with a white "C" works fine.

## Usage

1. **Start Convoq** locally: `python run.py` → `http://localhost:5000`
2. Open a **Google Meet** call
3. A floating **Convoq widget** appears in the bottom-right corner of the Meet page
4. Optionally enter a meeting title
5. Click **Start Recording** — the extension captures tab audio and sends 30-second chunks to Convoq for transcription
6. When the meeting ends, click **End & Summarise**
7. Convoq opens a new tab with the full AI summary, action items, decisions, and follow-up email

## How it works

```
Google Meet tab audio
        ↓
chrome.tabCapture (background SW)
        ↓
offscreen.js MediaRecorder (30-second WebM chunks)
        ↓
POST /api/transcribe-chunk (local Whisper)
        ↓
Accumulated transcript
        ↓
POST /process (Claude AI extraction)
        ↓
Convoq results page
```

## Notes

- Audio transcription requires `openai-whisper` installed (`pip install -r requirements.txt`)
- `ffmpeg` must be installed for Whisper to decode WebM audio (`winget install ffmpeg`)
- The extension only works while Convoq is running locally on port 5000
- For a production deployment, update `CONVOQ_BASE` in `background.js` to your live URL
