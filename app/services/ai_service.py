"""
AI processing module for Convoq.
Primary: Anthropic Claude for all text analysis.
Audio transcription: local openai-whisper (no API key, no cost).
"""

import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

_anthropic_client = None


def get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        from anthropic import Anthropic
        _anthropic_client = Anthropic(api_key=api_key)
    return _anthropic_client


# ── Meeting type templates ────────────────────────────────────────────────────

MEETING_TEMPLATES = {
    "general": {
        "label": "General Meeting",
        "hint": "This is a general business meeting. Extract all action items, decisions, and discussion topics.",
    },
    "sales": {
        "label": "Sales Call",
        "hint": (
            "This is a sales call or client meeting. Pay special attention to: "
            "pain points expressed, budget signals, decision-maker names, objections raised, "
            "next steps committed to, and follow-up promises."
        ),
    },
    "sprint": {
        "label": "Sprint Review / Planning",
        "hint": (
            "This is an agile sprint meeting. Focus on: completed stories, incomplete items, "
            "velocity discussion, blockers, next sprint commitments, and retrospective action items."
        ),
    },
    "board": {
        "label": "Board Meeting",
        "hint": (
            "This is a board-level or executive meeting. Focus on: strategic decisions, "
            "financial approvals, governance items, risk acceptance, and executive-level action items."
        ),
    },
    "standup": {
        "label": "Daily Standup",
        "hint": (
            "This is a daily standup. Extract what each person completed yesterday, "
            "what they plan to do today, and any blockers reported."
        ),
    },
}

EXTRACTION_SCHEMA = """
{
  "summary": ["concise point 1", "concise point 2", "..."],
  "action_items": [
    {
      "task": "specific action",
      "owner": "person name or 'Unassigned'",
      "due_date": "YYYY-MM-DD or 'TBD'",
      "priority": "High | Medium | Low",
      "source_quote": "the exact phrase from the transcript that implies this action"
    }
  ],
  "decisions": ["decision 1", "decision 2"],
  "risks": ["risk or blocker 1", "risk or blocker 2"],
  "sentiment": "Positive | Neutral | Negative | Tense | Productive",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "attendees": ["Name 1", "Name 2"],
  "follow_up_email": "ready-to-send follow-up email body (plain text, 150-200 words)"
}
"""

_EXTRACTION_SYSTEM = """You are Convoq, an expert AI meeting analyst and corporate secretary.
{hint}

Analyse the transcript and return STRICTLY valid JSON matching this schema:
{schema}

Rules:
- Extract 4-6 summary points.
- Extract ALL action items with inferred owners where possible.
- Priority: High = urgent/blocker/this week, Medium = normal, Low = nice-to-have.
- source_quote must be a short verbatim phrase from the transcript (max 20 words).
- follow_up_email should start with a greeting and close with "Best regards," and a blank signature line.
- Return ONLY the raw JSON object. No markdown code fences. No preamble. No explanation."""


def _strip_fences(text: str) -> str:
    """Remove markdown code fences Claude occasionally wraps around JSON."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def process_meeting_transcript(transcript_text: str, meeting_type: str = "general") -> dict:
    """Extract structured data from a meeting transcript using Claude."""
    template = MEETING_TEMPLATES.get(meeting_type, MEETING_TEMPLATES["general"])
    system_prompt = _EXTRACTION_SYSTEM.format(hint=template["hint"], schema=EXTRACTION_SCHEMA)

    client = get_anthropic_client()
    if client:
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=3000,
                system=system_prompt,
                messages=[{"role": "user", "content": f"Transcript:\n\n{transcript_text}"}],
            )
            raw = _strip_fences(response.content[0].text)
            return json.loads(raw)
        except Exception as exc:
            print(f"[Convoq AI] Anthropic extraction error: {exc}")

    return _mock_data()


def transcribe_audio(file_path: str) -> str:
    """Transcribe audio via Groq Whisper API (cloud) or local openai-whisper (local dev)."""
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from groq import Groq as GroqClient
            client = GroqClient(api_key=groq_key)
            with open(file_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=f,
                )
            return result.text.strip()
        except Exception as exc:
            print(f"[Convoq AI] Groq transcription error: {exc}")
            return ""

    # Fallback: local openai-whisper (works only in local dev with ffmpeg installed)
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(file_path)
        return result.get("text", "").strip()
    except ImportError:
        print("[Convoq AI] No transcription backend available. Set GROQ_API_KEY for cloud transcription.")
        return ""
    except Exception as exc:
        print(f"[Convoq AI] Whisper transcription error: {exc}")
        return ""


def chat_with_meeting_context(transcript_text: str, user_question: str) -> str:
    """Answer a question about a meeting transcript."""
    system = (
        "You are Convoq, a helpful meeting assistant. "
        "Answer questions about the meeting transcript provided. "
        "Be concise, specific, and factual. Only use information from the transcript."
    )

    client = get_anthropic_client()
    if client:
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                system=system,
                messages=[
                    {"role": "user", "content": f"Transcript:\n{transcript_text}\n\nQuestion: {user_question}"}
                ],
            )
            return response.content[0].text
        except Exception as exc:
            return f"Error: {exc}"

    return "AI features are not enabled. Add ANTHROPIC_API_KEY to your .env file."


def apply_recipe(prompt_template: str, transcript_text: str) -> str:
    """Run a saved recipe prompt against a meeting transcript."""
    full_prompt = f"{prompt_template}\n\nMeeting transcript:\n\n{transcript_text}"

    client = get_anthropic_client()
    if client:
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                messages=[{"role": "user", "content": full_prompt}],
            )
            return response.content[0].text
        except Exception as exc:
            print(f"[Convoq AI] Recipe error: {exc}")

    return "AI not available. Add ANTHROPIC_API_KEY to your .env file."


def generate_follow_up_email(meeting_title: str, summary: list, action_items: list, decisions: list) -> str:
    """Generate a polished follow-up email for a meeting."""
    items_text = "\n".join(
        f"- {i.get('task','?')} ({i.get('owner','?')}, due {i.get('due_date','TBD')})"
        for i in action_items
    )
    decisions_text = "\n".join(f"- {d}" for d in decisions)
    prompt = (
        f"Write a professional meeting follow-up email for '{meeting_title}'.\n"
        f"Summary points: {json.dumps(summary)}\n"
        f"Action items:\n{items_text}\n"
        f"Decisions made:\n{decisions_text}\n"
        "Keep it under 200 words. Plain text only. Start with 'Hi team,' and end with 'Best regards,'"
    )

    client = get_anthropic_client()
    if client:
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as exc:
            print(f"[Convoq AI] Email error: {exc}")

    return _mock_email(meeting_title, action_items)


# ── Fallbacks ─────────────────────────────────────────────────────────────────

def _mock_data() -> dict:
    return {
        "summary": [
            "Discussed project timeline and key deliverables for the upcoming quarter.",
            "Identified deployment risks and mitigation strategies.",
            "Agreed on marketing strategy and budget allocation for Q4.",
            "Team flagged capacity constraints in the engineering squad.",
            "Decided to move forward with Vendor A based on pricing and support.",
        ],
        "action_items": [
            {
                "task": "Prepare updated project timeline with milestones",
                "owner": "Sarah",
                "due_date": "TBD",
                "priority": "High",
                "source_quote": "we need the timeline ready before the client call",
            },
            {
                "task": "Fix critical login bug reported by QA",
                "owner": "Mike",
                "due_date": "TBD",
                "priority": "High",
                "source_quote": "the login issue has to be fixed this sprint",
            },
            {
                "task": "Schedule client demo and send calendar invites",
                "owner": "John",
                "due_date": "TBD",
                "priority": "Medium",
                "source_quote": "John can you set up the demo call",
            },
        ],
        "decisions": [
            "Approved new UI design with accessibility improvements.",
            "Feature launch postponed by one week to allow for QA completion.",
            "Vendor A selected for infrastructure contract.",
        ],
        "risks": [
            "Engineering capacity is at 90% — any new requests will slip the timeline.",
            "Third-party API dependency has no SLA — fallback plan needed.",
        ],
        "sentiment": "Productive",
        "keywords": ["Timeline", "Launch", "QA", "Vendor", "Capacity"],
        "attendees": ["Sarah", "Mike", "John"],
        "follow_up_email": (
            "Hi team,\n\nThank you for a productive session today. "
            "Here is a quick summary of what we covered and what comes next.\n\n"
            "Key decisions: we approved the new UI design and selected Vendor A. "
            "The feature launch is moved by one week to allow QA to complete.\n\n"
            "Action items:\n"
            "- Sarah: updated project timeline\n"
            "- Mike: fix critical login bug\n"
            "- John: schedule client demo\n\n"
            "Please update your items in Convoq as you make progress.\n\n"
            "Best regards,\n"
        ),
    }


def _mock_email(meeting_title: str, action_items: list) -> str:
    items = "\n".join(
        f"- {i.get('task', '?')} ({i.get('owner', 'TBD')})"
        for i in action_items[:5]
    )
    return (
        f"Hi team,\n\nThank you for joining today's '{meeting_title}' session.\n\n"
        f"Action items agreed:\n{items}\n\n"
        "Please update your tasks in Convoq as progress is made.\n\nBest regards,\n"
    )
