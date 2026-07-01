import json
import uuid
from datetime import datetime, date
from app.extensions import db


class ActionItem(db.Model):
    __tablename__ = "action_item"

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(
        db.Integer, db.ForeignKey("meeting.id", ondelete="CASCADE"), nullable=False
    )
    task = db.Column(db.Text, nullable=False)
    owner = db.Column(db.String(100), nullable=True)
    due_date = db.Column(db.String(50), nullable=True)
    priority = db.Column(db.String(20), default="Medium")  # High / Medium / Low
    status = db.Column(db.String(30), default="Open")      # Open / In Progress / Done / Blocked
    source_quote = db.Column(db.Text, nullable=True)
    recurring = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    meeting = db.relationship("Meeting", back_populates="action_items_rel")

    def is_overdue(self):
        if self.due_date and self.status != "Done":
            try:
                due = datetime.strptime(self.due_date, "%Y-%m-%d").date()
                return due < date.today()
            except ValueError:
                return False
        return False

    def to_dict(self):
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "task": self.task,
            "owner": self.owner or "Unassigned",
            "due_date": self.due_date or "TBD",
            "deadline": self.due_date or "TBD",  # legacy alias
            "priority": self.priority,
            "status": self.status,
            "source_quote": self.source_quote,
            "recurring": self.recurring,
            "notes": self.notes,
            "is_overdue": self.is_overdue(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "meeting_title": self.meeting.title if self.meeting else "",
        }


class Meeting(db.Model):
    __tablename__ = "meeting"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    meeting_type = db.Column(db.String(50), default="general")

    # AI-extracted content (JSON lists stored as text)
    summary = db.Column(db.Text, nullable=True)
    decisions = db.Column(db.Text, nullable=True)
    risks = db.Column(db.Text, nullable=True)
    follow_up_email = db.Column(db.Text, nullable=True)

    # Analysis
    sentiment = db.Column(db.String(50), nullable=True)
    keywords = db.Column(db.Text, nullable=True)
    attendees = db.Column(db.Text, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)

    original_transcript = db.Column(db.Text, nullable=False)

    # Sharing — unique token for public read-only access
    share_token = db.Column(db.String(36), nullable=True, unique=True)

    # Legacy column kept so existing DB rows don't break
    action_items = db.Column(db.Text, nullable=True)

    action_items_rel = db.relationship(
        "ActionItem",
        back_populates="meeting",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __init__(
        self,
        title,
        summary,
        decisions,
        original_transcript,
        meeting_type="general",
        sentiment="Neutral",
        keywords=None,
        risks=None,
        follow_up_email=None,
        attendees=None,
        duration_minutes=None,
    ):
        self.title = title
        self.meeting_type = meeting_type
        self.summary = json.dumps(summary) if isinstance(summary, list) else (summary or "[]")
        self.decisions = json.dumps(decisions) if isinstance(decisions, list) else (decisions or "[]")
        self.risks = json.dumps(risks if risks else [])
        self.follow_up_email = follow_up_email
        self.original_transcript = original_transcript
        self.sentiment = sentiment
        self.keywords = json.dumps(keywords if keywords else [])
        self.attendees = json.dumps(attendees if attendees else [])
        self.duration_minutes = duration_minutes

    def generate_share_token(self):
        if not self.share_token:
            self.share_token = str(uuid.uuid4())
        return self.share_token

    # ── Getters ──────────────────────────────────────────────────────────────

    def get_summary(self):
        try:
            return json.loads(self.summary) if self.summary else []
        except (ValueError, TypeError):
            return []

    def get_decisions(self):
        try:
            return json.loads(self.decisions) if self.decisions else []
        except (ValueError, TypeError):
            return []

    def get_risks(self):
        try:
            return json.loads(self.risks) if self.risks else []
        except (ValueError, TypeError):
            return []

    def get_keywords(self):
        try:
            return json.loads(self.keywords) if self.keywords else []
        except (ValueError, TypeError):
            return []

    def get_attendees(self):
        try:
            return json.loads(self.attendees) if self.attendees else []
        except (ValueError, TypeError):
            return []

    def get_action_items(self):
        """Returns action items preferring new table, falls back to legacy JSON."""
        items = self.action_items_rel.all()
        if items:
            return [i.to_dict() for i in items]
        try:
            legacy = json.loads(self.action_items) if self.action_items else []
            return legacy if isinstance(legacy, list) else []
        except (ValueError, TypeError):
            return []

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def open_count(self):
        return self.action_items_rel.filter_by(status="Open").count()

    @property
    def done_count(self):
        return self.action_items_rel.filter_by(status="Done").count()

    @property
    def total_count(self):
        return self.action_items_rel.count()

    @property
    def completion_rate(self):
        total = self.total_count
        return round((self.done_count / total) * 100) if total else 0

    @property
    def overdue_count(self):
        return sum(1 for i in self.action_items_rel.all() if i.is_overdue())


class Recipe(db.Model):
    """Reusable AI prompt templates (Granola-style recipes)."""
    __tablename__ = "recipe"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(30), default="bi-stars")
    description = db.Column(db.Text, nullable=True)
    prompt_template = db.Column(db.Text, nullable=False)
    is_builtin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "prompt_template": self.prompt_template,
            "is_builtin": self.is_builtin,
        }
