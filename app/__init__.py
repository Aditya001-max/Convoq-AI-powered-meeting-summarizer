from flask import Flask
from config import Config
from app.extensions import db


BUILTIN_RECIPES = [
    {
        "name": "Write Follow-up Email",
        "icon": "bi-envelope",
        "description": "Draft a professional follow-up email for all meeting attendees.",
        "prompt_template": (
            "Write a professional follow-up email based on this meeting transcript. "
            "Include: a brief summary, key decisions, and action items with owners. "
            "Keep it under 200 words, friendly and actionable. "
            "Start with 'Hi team,' and end with 'Best regards,'"
        ),
        "is_builtin": True,
    },
    {
        "name": "Extract Feature Requests",
        "icon": "bi-lightbulb",
        "description": "List all product feature requests and ideas mentioned.",
        "prompt_template": (
            "Extract all product feature requests, ideas, and enhancement suggestions from this meeting transcript. "
            "Format as a numbered list with: feature name, who requested it, business justification (if mentioned), "
            "and priority signal (urgent / nice-to-have)."
        ),
        "is_builtin": True,
    },
    {
        "name": "Executive Summary",
        "icon": "bi-briefcase",
        "description": "One-paragraph executive summary for leadership.",
        "prompt_template": (
            "Write a concise executive summary (3-4 sentences) of this meeting suitable for C-suite or board-level reporting. "
            "Focus on business outcomes, key decisions, and strategic implications. "
            "No bullet points — flowing, professional prose."
        ),
        "is_builtin": True,
    },
    {
        "name": "Risk & Blocker Report",
        "icon": "bi-exclamation-triangle",
        "description": "Extract all risks, blockers and concerns raised.",
        "prompt_template": (
            "Extract all risks, blockers, concerns, and impediments mentioned in this meeting transcript. "
            "For each, note: what the risk is, who raised it, current impact level (High/Medium/Low), "
            "and any proposed mitigation. Format as a structured numbered list."
        ),
        "is_builtin": True,
    },
    {
        "name": "PRD Snippet",
        "icon": "bi-file-earmark-text",
        "description": "Convert decisions into product requirements format.",
        "prompt_template": (
            "Convert the decisions and requirements discussed in this meeting into a Product Requirements Document (PRD) snippet. "
            "Include sections: Problem Statement, Goals, User Stories (as 'As a... I want... So that...'), "
            "and Acceptance Criteria. Use markdown formatting."
        ),
        "is_builtin": True,
    },
    {
        "name": "Coaching Feedback",
        "icon": "bi-person-check",
        "description": "Extract feedback, praise and development points.",
        "prompt_template": (
            "Extract all performance feedback, coaching points, praise, and development suggestions from this meeting. "
            "Group by person where identifiable. Format as: Strengths observed, Areas for development, "
            "Specific suggestions made."
        ),
        "is_builtin": True,
    },
    {
        "name": "Competitive Intelligence",
        "icon": "bi-trophy",
        "description": "Extract competitor mentions and market insights.",
        "prompt_template": (
            "Extract all mentions of competitors, market trends, customer feedback, and competitive positioning "
            "from this meeting transcript. Summarise: competitors mentioned, their perceived strengths/weaknesses, "
            "market opportunities identified, and strategic implications."
        ),
        "is_builtin": True,
    },
    {
        "name": "Next Steps Newsletter",
        "icon": "bi-newspaper",
        "description": "Format next steps as a concise team update.",
        "prompt_template": (
            "Format the next steps and action items from this meeting as a concise team newsletter update. "
            "Use a friendly, motivating tone. Include: what was accomplished, what comes next, "
            "who is responsible for what, and the key date to watch. Keep it under 150 words."
        ),
        "is_builtin": True,
    },
]


def _seed_recipes(app):
    """Insert built-in recipes if they don't exist yet."""
    from app.models import Recipe
    with app.app_context():
        for data in BUILTIN_RECIPES:
            exists = Recipe.query.filter_by(name=data["name"], is_builtin=True).first()
            if not exists:
                db.session.add(Recipe(**data))
        db.session.commit()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        import os as _os
        _os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        db.create_all()
        _seed_recipes(app)

    return app
