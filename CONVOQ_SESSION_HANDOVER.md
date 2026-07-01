# Convoq — Session Handover
**Date:** 2026-07-01  
**Project path:** `c:\Users\aarrk\Desktop\PROJECT_UPLOADS\AI-Powered-Corporate-Meeting-Minutes-Action-Tracker`  
**Repo branch:** `main`

---

## 1. What Convoq is

A Flask-based AI meeting intelligence app called **Convoq** (formerly "AI Meeting Minutes Tracker").

- Processes meeting transcripts (paste / upload / live record / Google Meet Chrome extension)
- Extracts: action items, decisions, risks, keywords, sentiment, attendees, follow-up email
- Manages tasks on a Kanban board across all meetings
- Analytics, People accountability, AI Recipes, Public share links, PDF export
- Google Meet Chrome Extension (MV3) for automatic in-call capture

---

## 2. Tech stack

| Layer | Choice |
|---|---|
| Backend | Flask 3.0, App Factory pattern, Blueprints |
| Database | SQLite via Flask-SQLAlchemy (dev) / PostgreSQL-ready |
| Text AI | Anthropic Claude `claude-haiku-4-5-20251001` |
| Audio transcription | Local `openai-whisper` (no API key, CPU-based, needs ffmpeg) |
| Frontend | Bootstrap 5.3 + custom `modern.css` (warm minimalistic) |
| Font | Inter (variable weight) |
| Chrome Extension | Manifest V3 — tabCapture + offscreen document pattern |

**Important:** OpenAI API is NOT used. Audio transcription uses the local `openai-whisper` Python package (free, runs on CPU).

---

## 3. File structure (key files)

```
├── run.py                          # Entry point: python run.py
├── config.py                       # Flask config (reads .env)
├── requirements.txt                # openai-whisper>=20231117 (not openai API)
├── .env                            # Real secrets — DO NOT commit
├── .env.example                    # Template
├── app/
│   ├── __init__.py                 # App factory
│   ├── extensions.py               # db = SQLAlchemy()
│   ├── models.py                   # Meeting, ActionItem, Recipe
│   ├── routes.py                   # All routes (Blueprint: main_bp)
│   ├── services/
│   │   ├── ai_service.py           # Claude + Whisper logic
│   │   ├── pdf_service.py          # PDF export
│   │   └── calendar_service.py     # Google Calendar OAuth
│   ├── static/
│   │   ├── css/modern.css          # Full design system (warm theme)
│   │   └── js/app.js               # Frontend JS
│   └── templates/
│       ├── base.html               # Navbar, announce bar, footer, floating Chrome CTA
│       ├── index.html              # PeakAI-inspired homepage (uses {% block full_content %})
│       ├── upload.html             # Upload/paste page
│       ├── record.html             # Live browser recording
│       ├── results.html            # AI output for a meeting
│       ├── past_meetings.html      # History list
│       ├── board.html              # Kanban board
│       ├── analytics.html          # Charts & stats
│       ├── people.html             # Per-person accountability
│       ├── recipes.html            # AI recipe templates
│       ├── calendar.html           # Google Calendar
│       ├── search.html             # Full-text search
│       └── share.html              # Public read-only meeting page
└── chrome-extension/
    ├── manifest.json               # MV3
    ├── background.js               # Service worker (tabCapture, chunk transcription)
    ├── offscreen.html/js           # MediaRecorder (30s WebM chunks)
    ├── content.js/css              # Floating widget injected into meet.google.com
    ├── popup.html/js               # Extension popup
    └── README.md                   # How to install and use
```

---

## 4. .env file (actual values in use)

```env
ANTHROPIC_API_KEY=sk-ant-api03-2HZO7CBTNzgNjUz4Wku4XYOHfD2ctWS7edRgCdehJJtMZSI9hVyu4eYCyM2XbqO9R9B1m6mkZlk4ne8AvYId6Q-I_HGHgAA
SECRET_KEY=ff85cd6d0019466502261dcf4430062ce567b4735c7880cf4e97106af1e21e2c
FLASK_ENV=development
OPENAI_API_KEY=
```

**Optional (not yet configured):**
```env
DATABASE_URL=postgresql://user:password@host/convoq   # for Vercel/production
GOOGLE_CLIENT_ID=...                                   # for Google Calendar
GOOGLE_CLIENT_SECRET=...
```

> **Security note:** The Anthropic key above was shared in chat and Google Docs in a previous session — it should be rotated at https://console.anthropic.com/ before any production use.

---

## 5. How to run locally

```bash
# 1. Activate venv (if using one)
python -m venv venv
venv\Scripts\activate      # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install ffmpeg (required for Whisper audio decoding)
winget install ffmpeg

# 4. Start the app
python run.py
# → http://localhost:5000
```

---

## 6. Design system (modern.css)

**Warm minimalistic theme** — inspired by https://thepeakai.com/

| Token | Value |
|---|---|
| `--bg` | `#FAFAF8` |
| `--accent` | `#C2410C` (terracotta/orange-red) |
| `--amber` | `#D97706` |
| `--green` | `#16A34A` |
| `--text` | `#1C1917` |
| `--text-2` | `#57534E` |
| `--text-3` | `#A8A29E` |
| `--border` | `#E7E5E4` |
| Font | Inter (variable, 300–900) |

Key CSS classes: `.bg-grid` (graph paper pattern), `.announce-bar`, `.chrome-float`, `.trust-pill`, `.hero-deco`, `.proof-strip`, `.feature-icon`, `.section-label`, `.text-gradient`, `.rec-dot`

---

## 7. Template inheritance pattern

`base.html` provides two content blocks:

```html
{% block full_content %}
  <div class="container my-4">{% block content %}{% endblock %}</div>
{% endblock %}
```

- **Most pages** use `{% block content %}` — gets auto-wrapped in `.container`
- **`index.html`** overrides `{% block full_content %}` directly — enables full-width sections (hero, metrics strip, feature grid, etc.)

---

## 8. Chrome Extension architecture

```
meet.google.com tab audio
        ↓
chrome.tabCapture (background.js service worker)
        ↓
offscreen.js — MediaRecorder, 30-second WebM chunks → base64
        ↓
POST /api/transcribe-chunk (local Whisper)
        ↓
accumulated transcript text
        ↓
POST /process (Claude AI extraction)
        ↓
Convoq results page (opens in new tab)
```

**To install the extension (dev mode):**
1. Place 3 PNG icons in `chrome-extension/icons/`: `icon16.png`, `icon48.png`, `icon128.png`
2. Open `chrome://extensions` → Enable Developer Mode → Load Unpacked → select `chrome-extension/`
3. Convoq must be running at `http://localhost:5000`

---

## 9. API routes summary

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Homepage |
| GET | `/upload` | Upload/paste transcript |
| GET | `/record` | Live browser recording |
| POST | `/process` | Process transcript → AI extraction → save → redirect to results |
| GET | `/results/<id>` | Meeting results page |
| GET | `/history` | All past meetings |
| GET | `/board` | Kanban task board |
| GET | `/analytics` | Charts & stats |
| GET | `/people` | Per-person accountability |
| GET | `/recipes` | AI recipe templates |
| GET | `/search` | Full-text search |
| GET | `/share/<token>` | Public read-only meeting page |
| GET | `/calendar` | Google Calendar view |
| GET/POST | `/calendar/auth`, `/calendar/callback`, `/calendar/disconnect` | Google OAuth |
| DELETE | `/delete_meeting/<id>` | Delete meeting |
| GET | `/export/<id>` | Export PDF |
| POST | `/api/chat` | Chat about a meeting transcript |
| GET | `/api/meetings` | JSON list of all meetings |
| PATCH | `/api/action-items/<id>` | Update action item |
| POST | `/api/action-items` | Create action item |
| POST | `/api/meetings/<id>/share` | Generate share link |
| DELETE | `/api/meetings/<id>/share` | Revoke share link |
| POST | `/api/recipes` | Create custom recipe |
| DELETE | `/api/recipes/<id>` | Delete custom recipe |
| POST | `/api/recipes/<id>/run` | Run recipe against a meeting |
| POST | `/api/transcribe-chunk` | Transcribe WebM audio chunk (Chrome ext) |

CORS headers are applied in `routes.py` (`@main_bp.after_request`) to allow requests from `chrome-extension://` origins.

---

## 10. Database models

**`Meeting`** — title, summary (JSON list), decisions (JSON list), original_transcript, meeting_type, sentiment, keywords (JSON list), risks (JSON list), follow_up_email, attendees (JSON list), share_token, date_created  
**`ActionItem`** — meeting_id (FK), task, owner, due_date, priority (High/Medium/Low), status (Open/In Progress/Blocked/Done), notes, source_quote, created_at, updated_at  
**`Recipe`** — name, icon, description, prompt_template, is_builtin, created_at  

Built-in recipes are seeded on first run (8 templates including follow-up email, risk report, PRD snippet, etc.)

---

## 11. What is DONE ✅

- [x] Full Flask app running locally
- [x] Anthropic Claude integration (claude-haiku-4-5-20251001)
- [x] OpenAI API removed — replaced with local Whisper
- [x] PeakAI-inspired UI redesign (warm theme, graph paper hero, decorative squares, pill CTAs)
- [x] Announcement bar (dismissible)
- [x] Floating "Add to Chrome" button (fixed bottom-right)
- [x] All 8 AI Recipes
- [x] Kanban board (drag-and-drop)
- [x] Analytics dashboard (Chart.js)
- [x] People accountability page
- [x] Public share links
- [x] Live browser recording (MediaRecorder)
- [x] PDF export
- [x] Full-text search
- [x] Google Calendar integration (OAuth, requires credentials)
- [x] Chrome Extension (full MV3 architecture — code complete, untested)
- [x] CORS headers for Chrome extension
- [x] Jinja2 TemplateSyntaxError fixed (apostrophe in feature tuple)

---

## 12. What is PENDING ⏳

### A. Chrome Extension — needs testing
1. Add 3 PNG icons to `chrome-extension/icons/` (16, 48, 128px — orange `#C2410C` with white "C")
2. Load unpacked in Chrome developer mode
3. Join a Google Meet call and test the floating widget
4. Test Start Recording → End & Summarise flow
5. Verify transcript appears correctly in Convoq results

### B. End-to-end testing checklist (not yet done)
- [ ] Upload a text transcript → verify AI extraction works
- [ ] Upload an audio file → verify local Whisper transcription
- [ ] Live browser recording → submit → verify results
- [ ] Run an AI recipe against a processed meeting
- [ ] Generate + open a share link
- [ ] Board drag-and-drop
- [ ] Analytics page loads without errors
- [ ] PDF export

### C. Vercel deployment (discussed but not started)
Steps to do:
1. Sign up at https://neon.tech → create PostgreSQL DB → copy `DATABASE_URL`
2. Set `DATABASE_URL` in `.env` (SQLAlchemy picks it up automatically)
3. Handle audio transcription on serverless — local Whisper **will not work** on Vercel. Options:
   - Use AssemblyAI or Deepgram free tier for audio (add `ASSEMBLY_AI_KEY` to env)
   - Or disable audio transcription on Vercel (text-only mode)
4. Add `vercel.json`:
   ```json
   {
     "builds": [{"src": "api/index.py", "use": "@vercel/python"}],
     "routes": [{"src": "/(.*)", "dest": "api/index.py"}]
   }
   ```
5. Add `api/index.py` WSGI adapter:
   ```python
   from app import create_app
   app = create_app()
   ```
6. `vercel deploy` — set env vars in Vercel dashboard (ANTHROPIC_API_KEY, SECRET_KEY, DATABASE_URL)

### D. Minor polish (optional)
- [x] `.env.example` still shows `OPENAI_API_KEY` — should be updated to remove it (minor)
- [ ] Flash message in `routes.py:370` still says "Ensure OPENAI_API_KEY is set for Whisper" — should say "Ensure openai-whisper and ffmpeg are installed"

---

## 13. Known issues / watch-outs

| Issue | Status |
|---|---|
| Anthropic API key was shared in chat/Google Docs | **Rotate it** at console.anthropic.com before production |
| Local Whisper loads model on every request (slow) | Acceptable for dev; cache the model in production |
| Whisper requires ffmpeg installed system-wide | `winget install ffmpeg` on Windows |
| Chrome extension icons not created yet | Must add before loading extension in Chrome |
| Stale error message for audio transcription (routes.py:370) | Still says OpenAI — cosmetic, app still works |

---

## 14. How to start next session

1. Read this file
2. Check memory files at `C:\Users\aarrk\.claude\projects\...\memory\`
3. Run `python run.py` to verify the app starts cleanly
4. Pick up from **Section 12 — Pending** above

The app is functionally complete for local use. The main remaining work is: Chrome extension testing (add icons → install → test), end-to-end feature verification, and Vercel deployment.
