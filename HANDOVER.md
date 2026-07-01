# Convoq — Session Handover
**Date:** 2026-07-01 | **Owner:** Aditya Raj Kaushik (aditya.kaushik@yallo.co) | **GitHub:** Aditya001-max

---

## Quick Start

```bash
cd "c:\Users\aarrk\Desktop\PROJECT_UPLOADS\AI-Powered-Corporate-Meeting-Minutes-Action-Tracker"
pip install -r requirements.txt
python run.py
# → http://localhost:5000
```

Make sure `.env` exists with at minimum `ANTHROPIC_API_KEY`. Copy from `.env.example` if missing.

---

## What is Convoq

AI-powered meeting minutes and action tracker. Flask 3.0 web app. Originally named CorpMeet-AI and built by an intern (Jani-shiv / Shiv Jani). Aditya took full ownership — all attribution has been replaced with Aditya Raj Kaushik / aditya.kaushik@yallo.co.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3.0, App Factory pattern, Blueprints (`main_bp`) |
| Database | SQLite via Flask-SQLAlchemy (`instance/convoq.db`) |
| Primary AI | Anthropic Claude `claude-haiku-4-5-20251001` via `anthropic>=0.30.0` SDK |
| Audio transcription | OpenAI Whisper `whisper-1` via `openai` SDK (ONLY for audio, not text) |
| PDF export | ReportLab |
| Frontend | Bootstrap 5 + Glassmorphism CSS (`app/static/css/modern.css`) + vanilla JS |
| Charts | Chart.js (CDN) |
| File parsing | python-docx |
| Calendar OAuth | google-auth-oauthlib + google-api-python-client |

---

## Environment Variables

```env
ANTHROPIC_API_KEY=sk-ant-...       # REQUIRED — all AI text features
OPENAI_API_KEY=sk-...              # Required only for audio upload + live recording
SECRET_KEY=some-random-string      # Flask session signing
GOOGLE_CLIENT_ID=...               # Optional — Google Calendar integration
GOOGLE_CLIENT_SECRET=...           # Optional — Google Calendar integration
```

---

## Database Models

### `Meeting`
Fields: `id, title, date_created, meeting_type, summary (JSON), decisions (JSON), risks (JSON), follow_up_email, sentiment, keywords (JSON), attendees (JSON), duration_minutes, original_transcript, share_token (UUID nullable), action_items (legacy JSON)`

Relationship: `action_items_rel → ActionItem` (cascade delete)

Methods: `get_summary(), get_decisions(), get_risks(), get_keywords(), get_attendees(), get_action_items(), generate_share_token()`

Properties: `open_count, done_count, total_count, completion_rate, overdue_count`

### `ActionItem`
Fields: `id, meeting_id (FK), task, owner, due_date, priority (High/Medium/Low), status (Open/In Progress/Done/Blocked), source_quote, recurring, notes, created_at, updated_at`

Methods: `is_overdue(), to_dict()`

### `Recipe`
Fields: `id, name, icon (Bootstrap icon class), description, prompt_template, is_builtin (bool), created_at`

8 built-in recipes are seeded automatically on app startup via `_seed_recipes()` in `app/__init__.py`. Seeding is idempotent (checks before inserting).

---

## All Routes

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Homepage with KPI cards |
| `/upload` | GET | Upload or paste transcript form |
| `/record` | GET | Live browser recording + scratchpad (Granola-inspired) |
| `/process` | POST | AI processes transcript → save → redirect to results |
| `/results/<id>` | GET | Meeting results: share button, run recipe modal |
| `/history` | GET | All past meetings list |
| `/board` | GET | Kanban drag-and-drop action item board |
| `/analytics` | GET | Charts and KPI analytics |
| `/people` | GET | Per-person accountability view |
| `/search` | GET | Full-text search across meetings |
| `/recipes` | GET | Recipe manager (built-in + custom) |
| `/share/<token>` | GET | Public read-only meeting view (no auth, no nav) |
| `/calendar` | GET | Google Calendar upcoming meetings |
| `/calendar/auth` | GET | Start Google OAuth2 flow |
| `/calendar/callback` | GET | Google OAuth2 callback handler |
| `/calendar/disconnect` | GET | Clear Google session credentials |
| `/delete_meeting/<id>` | POST | Delete a meeting record |
| `/export/<id>` | GET | Export meeting as PDF |
| `/api/chat` | POST | Chat with Claude about a meeting |
| `/api/meetings` | GET | JSON list of all meetings |
| `/api/action-items/<id>` | PATCH | Update action item fields |
| `/api/action-items` | POST | Create new action item |
| `/api/meetings/<id>/share` | POST | Generate share token for meeting |
| `/api/meetings/<id>/share` | DELETE | Revoke share token |
| `/api/recipes` | POST | Create a custom recipe |
| `/api/recipes/<id>` | DELETE | Delete a custom recipe |
| `/api/recipes/<id>/run` | POST | Run a recipe against a meeting transcript |
| `/api/transcribe-chunk` | POST | Transcribe 30s audio chunk (live recording) |

---

## All Files — Status and Purpose

| File | Status | Notes |
|---|---|---|
| `run.py` | Unchanged | Entry point — `python run.py` |
| `config.py` | Updated | Added `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| `requirements.txt` | Updated | Added `anthropic>=0.30.0`, `google-auth-oauthlib>=1.0.0`, `google-api-python-client>=2.0.0` |
| `.env.example` | Updated | Documents all 5 keys with setup instructions |
| `app/__init__.py` | Updated | App factory; seeds 8 built-in recipes on `db.create_all()` |
| `app/extensions.py` | Unchanged | SQLAlchemy `db` singleton |
| `app/models.py` | Updated | Added `share_token` to Meeting; added `Recipe` model |
| `app/routes.py` | Updated | All 28 routes including 8 new Granola-era routes |
| `app/services/ai_service.py` | Rewritten | Anthropic primary, OpenAI fallback; `_strip_fences()` for JSON safety |
| `app/services/calendar_service.py` | New | Google Calendar OAuth2 service |
| `app/services/pdf_service.py` | Unchanged | ReportLab PDF export |
| `app/templates/base.html` | Updated | Nav: Record, Calendar, Recipes; footer: Claude AI |
| `app/templates/index.html` | Updated | Homepage KPIs |
| `app/templates/upload.html` | Unchanged | Upload/paste form |
| `app/templates/record.html` | New | Live recording: MediaRecorder, Web Audio waveform, scratchpad |
| `app/templates/results.html` | Updated | Share panel + recipe runner modal |
| `app/templates/share.html` | New | Public standalone page (no base.html) |
| `app/templates/recipes.html` | New | Recipe cards + run-on-meeting modal |
| `app/templates/calendar.html` | New | Calendar connect / event list |
| `app/templates/board.html` | Unchanged | Kanban drag-and-drop |
| `app/templates/analytics.html` | Unchanged | Chart.js analytics |
| `app/templates/people.html` | Unchanged | Per-person view |
| `app/templates/search.html` | Unchanged | Full-text search |
| `app/templates/past_meetings.html` | Unchanged | History list |

---

## Features Built — Full List

### Session 1 (original + Aditya takeover)
- Upload transcript (text paste or file) → AI extraction → results
- Action items with Kanban board (HTML5 drag-and-drop, no React)
- Analytics dashboard (Chart.js)
- Per-person accountability view
- Full-text search
- PDF export (ReportLab)
- Chat with meeting context (Claude)
- Renamed project to Convoq; removed intern attribution

### Session 2 (Granola-inspired features)
- **Switched AI engine** from OpenAI GPT-4o-mini → Anthropic Claude (`claude-haiku-4-5-20251001`)
- **OpenAI Whisper** kept exclusively for audio file transcription
- **Live browser recording** (`/record`) — MediaRecorder API, 30s chunks, Web Audio waveform canvas, scratchpad textarea, pause/resume, timer
- **Scratchpad enrichment** — host notes prepended to transcript before AI processing
- **Meeting Recipes** — 8 built-in reusable AI prompt templates; custom recipe CRUD; run against any meeting
- **Shareable meeting links** — UUID token, public read-only `/share/<token>` page, revocable
- **Google Calendar integration** — OAuth2 connect, upcoming events list, Record-from-event button
- `_strip_fences()` utility to handle Claude occasionally wrapping JSON in markdown code fences

---

## Key AI Service Patterns

```python
# Anthropic primary — fallback to OpenAI GPT-4o-mini — fallback to mock data
# JSON mode workaround: explicit system prompt + _strip_fences()
def _strip_fences(text):
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

# Audio: ONLY via OpenAI Whisper (Anthropic has no audio API)
def transcribe_audio(file_path):
    client = get_openai_client()  # separate singleton
    ...
```

---

## Runtime Verification Status (as of 2026-07-01)

| Feature | Status |
|---|---|
| Core upload + AI extraction | Verified working in previous session |
| Kanban board, analytics, search, PDF | Verified working in previous session |
| Chat with meeting context | Verified working |
| Live recording (`/record`) | Code-complete, **not yet end-to-end tested** |
| Share link + public page | Code-complete, **not yet end-to-end tested** |
| Recipe manager + runner | Code-complete, **not yet end-to-end tested** |
| Google Calendar OAuth | Code-complete, **requires Google Cloud credentials** |

**Most likely first-run issue:** Existing `instance/convoq.db` won't have `share_token` or `recipe` table. SQLAlchemy's `db.create_all()` adds them automatically on startup — no manual migration needed.

---

## First-run Checklist for New Session

- [ ] `pip install -r requirements.txt`
- [ ] `.env` exists with `ANTHROPIC_API_KEY` set
- [ ] `python run.py` — confirm no import errors
- [ ] Open `http://localhost:5000` — confirm homepage loads
- [ ] Upload or paste a transcript — confirm results page works
- [ ] Visit `/record` — confirm recording controls render
- [ ] Visit `/recipes` — confirm 8 built-in recipes appear
- [ ] On a results page — test Share button → copy link → open in incognito
- [ ] On a results page — test Run Recipe → select a recipe → confirm output

---

## Out of Scope (deliberately not built)

- Desktop app / system audio capture (needs Electron)
- Zoom/Teams bot join (needs Recall.ai or similar paid API)
- Speaker diarisation (needs GPU or paid service)
- Semantic search / pgvector (needs PostgreSQL migration)
- Jira / Linear / Slack push integrations
- SSO / SAML authentication
- Mobile apps

---

## Git State

Latest commit: `49fafb9` — "refactor: restructure project into a modular Flask application..."

All Session 2 changes (AI switch, Granola features) are **working tree changes only — not yet committed**. The git log does not reflect them. Commit before pushing.

---

## How to Brief Claude in a New Session

Paste this at the start:

> "Continue work on Convoq. Read HANDOVER.md in the project root and the memory files at `~/.claude/projects/.../memory/`. The project is at `c:\Users\aarrk\Desktop\PROJECT_UPLOADS\AI-Powered-Corporate-Meeting-Minutes-Action-Tracker`."

Claude's memory system will auto-load `user_profile.md`, `project_convoq.md`, and `feedback_style.md` — no need to re-explain who you are or what the project is.
