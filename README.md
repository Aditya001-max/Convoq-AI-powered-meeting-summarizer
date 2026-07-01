# Convoq — AI Meeting Intelligence

**Turn any meeting transcript into action in seconds.**
No manual note-taking. No missed follow-ups. No friction.

[![License: MIT](https://img.shields.io/badge/License-MIT-black?style=flat-square)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-black?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![AI Powered](https://img.shields.io/badge/AI-Powered-black?style=flat-square)](https://github.com/Aditya001-max/Convoq-AI-powered-meeting-summarizer)

---

## What it does

Paste a transcript, upload a file, or record live — Convoq does the rest.

- **Action items** extracted with owners, deadlines, and priority
- **Meeting summary** in 4–6 sharp bullet points
- **Decisions & risks** surfaced automatically
- **Follow-up email** drafted and ready to send
- **Kanban board** to track tasks across every meeting
- **Analytics dashboard** with sentiment, keywords, and completion rates
- **AI Recipes** — reusable prompt templates (executive summary, PRD snippet, risk report, and more)
- **Public share links** — send a read-only meeting view to anyone
- **Live browser recording** — capture directly in the browser, no desktop app needed
- **PDF export** — professional meeting minutes, one click
- **Full-text search** across all meetings
- **Per-person accountability** view
- **Google Meet Chrome Extension** — automatic in-call capture (MV3)
- **Google Calendar integration** — see upcoming meetings and record from them

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Flask 3.0, App Factory, Blueprints |
| Database | SQLite (local) · PostgreSQL via Neon (production) |
| AI — text | Convoq AI Engine |
| AI — audio | Groq Whisper API (cloud) · local openai-whisper (dev) |
| Frontend | Bootstrap 5 · custom warm minimalistic CSS · Chart.js |
| PDF | ReportLab |
| Chrome Extension | Manifest V3 — tabCapture + offscreen document |

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/Aditya001-max/Convoq-AI-powered-meeting-summarizer.git
cd Convoq-AI-powered-meeting-summarizer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY at minimum

# 4. Run
python run.py
# → http://localhost:5000
```

Convoq creates its SQLite database and seeds all built-in AI recipes on first run. No migrations needed.

---

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `AI_API_KEY` | Yes | All AI text features |
| `GROQ_API_KEY` | For audio | Cloud audio transcription (free tier: 7,200s/day) |
| `SECRET_KEY` | Yes (prod) | Flask session signing |
| `DATABASE_URL` | For prod | PostgreSQL connection string (Neon, Supabase, etc.) |
| `GOOGLE_CLIENT_ID` | Optional | Google Calendar integration |
| `GOOGLE_CLIENT_SECRET` | Optional | Google Calendar integration |

See `.env.example` for setup instructions.

---

## Deploying to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel

# Set production environment variables
vercel env add ANTHROPIC_API_KEY
vercel env add GROQ_API_KEY
vercel env add DATABASE_URL   # PostgreSQL from Neon
vercel env add SECRET_KEY

# Production deploy
vercel --prod
```

The app is fully Vercel-ready — `vercel.json` and `api/index.py` are already configured.

---

## Project structure

```
├── run.py                       # Entry point
├── config.py                    # Flask config (reads .env)
├── vercel.json                  # Vercel deployment config
├── api/index.py                 # Vercel WSGI entry point
├── requirements.txt
├── app/
│   ├── __init__.py              # App factory + recipe seeding
│   ├── models.py                # Meeting, ActionItem, Recipe
│   ├── routes.py                # All routes (28 endpoints)
│   ├── services/
│   │   ├── ai_service.py        # AI engine + Groq Whisper
│   │   ├── pdf_service.py       # ReportLab PDF export
│   │   └── calendar_service.py  # Google Calendar OAuth
│   ├── static/
│   │   ├── css/modern.css       # Full design system
│   │   └── js/app.js
│   └── templates/               # 14 Jinja2 templates
└── chrome-extension/            # MV3 extension for Google Meet
```

---

## AI Recipes (built-in)

Eight reusable prompt templates you can run against any meeting:

| Recipe | Output |
|---|---|
| Write Follow-up Email | Ready-to-send team email |
| Executive Summary | 3–4 sentence C-suite brief |
| Risk & Blocker Report | Structured risk list with severity |
| Extract Feature Requests | Numbered product feature list |
| PRD Snippet | User stories + acceptance criteria |
| Coaching Feedback | Per-person strengths and development points |
| Competitive Intelligence | Competitor mentions and market signals |
| Next Steps Newsletter | Short motivating team update |

Custom recipes can be created and saved from the /recipes page.

---

## Chrome Extension

Convoq includes a full Manifest V3 Chrome extension that captures Google Meet audio directly in the browser.

**To install (developer mode):**
1. Add three PNG icons to `chrome-extension/icons/` — `icon16.png`, `icon48.png`, `icon128.png`
2. Open `chrome://extensions` → Enable Developer Mode → Load Unpacked → select the `chrome-extension/` folder
3. Convoq must be running at `http://localhost:5000`

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built by [Aditya Raj Kaushik](https://github.com/Aditya001-max)*
