import os
import uuid
from collections import defaultdict
from datetime import datetime, date

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    flash,
    send_file,
    session,
    url_for,
    current_app,
)
from werkzeug.utils import secure_filename
from docx import Document

from app.extensions import db
from app.models import ActionItem, Meeting, Recipe
from app.services.ai_service import (
    MEETING_TEMPLATES,
    apply_recipe,
    chat_with_meeting_context,
    process_meeting_transcript,
    transcribe_audio,
)
from app.services.pdf_service import create_meeting_minutes_pdf

main_bp = Blueprint("main", __name__)

# Allow the Chrome extension (meet.google.com) to call our API endpoints
EXTENSION_ORIGINS = {
    "https://meet.google.com",
    "chrome-extension://",   # matched as prefix below
}


@main_bp.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "")
    if origin.startswith("chrome-extension://") or origin in EXTENSION_ORIGINS:
        response.headers["Access-Control-Allow-Origin"]  = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@main_bp.route("/api/transcribe-chunk", methods=["OPTIONS"])
@main_bp.route("/api/action-items", methods=["OPTIONS"])
@main_bp.route("/process", methods=["OPTIONS"])
def cors_preflight():
    response = jsonify({})
    origin = request.headers.get("Origin", "")
    if origin.startswith("chrome-extension://"):
        response.headers["Access-Control-Allow-Origin"]  = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response, 200


TEXT_EXTENSIONS = {"txt", "docx"}
AUDIO_EXTENSIONS = {"mp3", "mp4", "wav", "m4a", "webm", "ogg"}
ALL_EXTENSIONS = TEXT_EXTENSIONS | AUDIO_EXTENSIONS


def _allowed(filename, exts=ALL_EXTENSIONS):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in exts


def _extract_text(file_path):
    try:
        if file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif file_path.endswith(".docx"):
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
    except Exception as exc:
        print(f"[Convoq] Text extract error: {exc}")
    return None


def _save_action_items(meeting, raw_items):
    """Persist AI-extracted action items as ActionItem rows."""
    for item in raw_items:
        ai = ActionItem(
            meeting_id=meeting.id,
            task=item.get("task", ""),
            owner=item.get("owner") or "Unassigned",
            due_date=item.get("due_date") or item.get("deadline") or "TBD",
            priority=item.get("priority", "Medium"),
            status="Open",
            source_quote=item.get("source_quote"),
        )
        db.session.add(ai)


# ── Pages ─────────────────────────────────────────────────────────────────────

@main_bp.route("/")
def homepage():
    total_meetings = Meeting.query.count()
    total_items = ActionItem.query.count()
    done_items = ActionItem.query.filter_by(status="Done").count()
    return render_template(
        "index.html",
        total_meetings=total_meetings,
        total_items=total_items,
        done_items=done_items,
    )


@main_bp.route("/upload")
def upload_page():
    return render_template("upload.html", meeting_types=MEETING_TEMPLATES)


@main_bp.route("/record")
def record():
    """Live browser recording page with split-pane scratchpad."""
    prefill_title = request.args.get("title", "")
    prefill_attendees = request.args.get("attendees", "")
    prefill_type = request.args.get("type", "general")
    return render_template(
        "record.html",
        meeting_types=MEETING_TEMPLATES,
        prefill_title=prefill_title,
        prefill_attendees=prefill_attendees,
        prefill_type=prefill_type,
    )


@main_bp.route("/history")
def past_meetings():
    meetings = Meeting.query.order_by(Meeting.date_created.desc()).all()
    return render_template("past_meetings.html", meetings=meetings)


@main_bp.route("/results/<int:meeting_id>")
def view_results(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    recipes = Recipe.query.order_by(Recipe.is_builtin.desc(), Recipe.name).all()
    return render_template("results.html", meeting=meeting, recipes=recipes)


@main_bp.route("/board")
def board():
    items = ActionItem.query.order_by(ActionItem.created_at.desc()).all()
    columns = {"Open": [], "In Progress": [], "Blocked": [], "Done": []}
    for item in items:
        columns.get(item.status, columns["Open"]).append(item)

    total = len(items)
    done = len(columns["Done"])
    accountability = round((done / total) * 100) if total else 0

    return render_template("board.html", columns=columns, accountability=accountability, total=total)


@main_bp.route("/analytics")
def analytics():
    meetings = Meeting.query.order_by(Meeting.date_created.asc()).all()
    items = ActionItem.query.all()

    total_meetings = len(meetings)
    total_items = len(items)
    done_items = sum(1 for i in items if i.status == "Done")
    overdue_items = sum(1 for i in items if i.is_overdue())
    completion_rate = round((done_items / total_items) * 100) if total_items else 0

    type_counts = defaultdict(int)
    for m in meetings:
        type_counts[m.meeting_type.title()] += 1

    priority_counts = {"High": 0, "Medium": 0, "Low": 0}
    for i in items:
        priority_counts[i.priority] = priority_counts.get(i.priority, 0) + 1

    owner_stats = defaultdict(lambda: {"total": 0, "done": 0, "overdue": 0})
    for i in items:
        owner = i.owner or "Unassigned"
        owner_stats[owner]["total"] += 1
        if i.status == "Done":
            owner_stats[owner]["done"] += 1
        if i.is_overdue():
            owner_stats[owner]["overdue"] += 1

    top_owners = sorted(
        [
            {
                "name": k,
                "total": v["total"],
                "done": v["done"],
                "overdue": v["overdue"],
                "rate": round((v["done"] / v["total"]) * 100) if v["total"] else 0,
            }
            for k, v in owner_stats.items()
        ],
        key=lambda x: x["total"],
        reverse=True,
    )[:10]

    monthly = defaultdict(int)
    for m in meetings:
        monthly[m.date_created.strftime("%b %Y")] += 1
    monthly_labels = list(monthly.keys())[-12:]
    monthly_values = [monthly[k] for k in monthly_labels]

    return render_template(
        "analytics.html",
        total_meetings=total_meetings,
        total_items=total_items,
        done_items=done_items,
        overdue_items=overdue_items,
        completion_rate=completion_rate,
        type_counts=dict(type_counts),
        priority_counts=priority_counts,
        top_owners=top_owners,
        monthly_labels=monthly_labels,
        monthly_values=monthly_values,
    )


@main_bp.route("/people")
def people():
    items = ActionItem.query.order_by(ActionItem.due_date).all()
    owner_map = defaultdict(lambda: {"open": [], "in_progress": [], "done": [], "blocked": []})
    for item in items:
        owner = item.owner or "Unassigned"
        bucket = item.status.lower().replace(" ", "_")
        if bucket in owner_map[owner]:
            owner_map[owner][bucket].append(item)
        else:
            owner_map[owner]["open"].append(item)

    people_list = []
    for name, buckets in owner_map.items():
        all_items = buckets["open"] + buckets["in_progress"] + buckets["done"] + buckets["blocked"]
        total = len(all_items)
        done = len(buckets["done"])
        overdue = sum(1 for i in all_items if i.is_overdue())
        people_list.append({
            "name": name,
            "total": total,
            "done": done,
            "open": len(buckets["open"]),
            "in_progress": len(buckets["in_progress"]),
            "blocked": len(buckets["blocked"]),
            "overdue": overdue,
            "rate": round((done / total) * 100) if total else 0,
            "items": all_items,
        })

    people_list.sort(key=lambda x: x["overdue"], reverse=True)
    return render_template("people.html", people_list=people_list)


@main_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        like = f"%{q}%"
        results = Meeting.query.filter(
            db.or_(
                Meeting.title.ilike(like),
                Meeting.original_transcript.ilike(like),
                Meeting.summary.ilike(like),
                Meeting.decisions.ilike(like),
                Meeting.keywords.ilike(like),
            )
        ).order_by(Meeting.date_created.desc()).all()
    return render_template("search.html", results=results, query=q)


@main_bp.route("/recipes")
def recipes():
    all_recipes = Recipe.query.order_by(Recipe.is_builtin.desc(), Recipe.name).all()
    return render_template("recipes.html", recipes=all_recipes)


@main_bp.route("/share/<token>")
def share_meeting(token):
    """Public read-only meeting summary page."""
    meeting = Meeting.query.filter_by(share_token=token).first_or_404()
    return render_template("share.html", meeting=meeting)


# ── Google Calendar ────────────────────────────────────────────────────────────

@main_bp.route("/calendar")
def calendar_view():
    from app.services.calendar_service import get_upcoming_events, is_connected
    connected = is_connected()
    events = get_upcoming_events() if connected else []
    return render_template("calendar.html", connected=connected, events=events)


@main_bp.route("/calendar/auth")
def calendar_auth():
    from app.services.calendar_service import get_auth_url
    auth_url = get_auth_url()
    if not auth_url:
        flash("Google Calendar credentials not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env", "error")
        return redirect(url_for("main.calendar_view"))
    return redirect(auth_url)


@main_bp.route("/calendar/callback")
def calendar_callback():
    from app.services.calendar_service import exchange_code
    code = request.args.get("code")
    if not code:
        flash("Google authorisation failed.", "error")
        return redirect(url_for("main.calendar_view"))
    exchange_code(code)
    flash("Google Calendar connected successfully!", "success")
    return redirect(url_for("main.calendar_view"))


@main_bp.route("/calendar/disconnect")
def calendar_disconnect():
    session.pop("google_credentials", None)
    flash("Google Calendar disconnected.", "success")
    return redirect(url_for("main.calendar_view"))


# ── Processing ────────────────────────────────────────────────────────────────

@main_bp.route("/process", methods=["POST"])
def process_transcript():
    transcript_text = ""
    title = request.form.get("meeting_title", "Untitled Meeting").strip() or "Untitled Meeting"
    meeting_type = request.form.get("meeting_type", "general")
    manual_attendees = [
        a.strip() for a in request.form.get("attendees", "").split(",") if a.strip()
    ]
    scratchpad_notes = request.form.get("scratchpad_notes", "").strip()

    # 1. Text paste
    pasted = request.form.get("transcript_text", "").strip()
    if pasted:
        transcript_text = pasted

    # 2. Text / DOCX file
    if not transcript_text:
        file = request.files.get("transcript_file")
        if file and file.filename and _allowed(file.filename, TEXT_EXTENSIONS):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            transcript_text = _extract_text(filepath) or ""
            os.remove(filepath)

    # 3. Audio file → Whisper (includes live recording blob)
    if not transcript_text:
        audio = request.files.get("audio_file")
        if audio and audio.filename and _allowed(audio.filename, AUDIO_EXTENSIONS):
            filename = secure_filename(audio.filename)
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            audio.save(filepath)
            transcript_text = transcribe_audio(filepath)
            os.remove(filepath)
            if not transcript_text:
                flash("Audio transcription failed. Ensure GROQ_API_KEY is set in your environment.", "error")
                return redirect(url_for("main.upload_page"))

    # Prepend scratchpad notes to transcript for richer AI context
    if scratchpad_notes and transcript_text:
        transcript_text = f"[Meeting notes by host]\n{scratchpad_notes}\n\n[Transcript]\n{transcript_text}"
    elif scratchpad_notes:
        transcript_text = scratchpad_notes

    if not transcript_text or len(transcript_text) < 20:
        flash("Transcript too short or missing. Please paste text or upload a file.", "error")
        return redirect(url_for("main.upload_page"))

    try:
        ai = process_meeting_transcript(transcript_text, meeting_type=meeting_type)
        attendees = ai.get("attendees") or manual_attendees or []

        meeting = Meeting(
            title=title,
            summary=ai.get("summary", []),
            decisions=ai.get("decisions", []),
            original_transcript=transcript_text,
            meeting_type=meeting_type,
            sentiment=ai.get("sentiment", "Neutral"),
            keywords=ai.get("keywords", []),
            risks=ai.get("risks", []),
            follow_up_email=ai.get("follow_up_email"),
            attendees=attendees,
        )
        db.session.add(meeting)
        db.session.flush()

        _save_action_items(meeting, ai.get("action_items", []))
        db.session.commit()

        flash("Meeting processed successfully!", "success")
        return redirect(url_for("main.view_results", meeting_id=meeting.id))

    except Exception as exc:
        db.session.rollback()
        print(f"[Convoq] Processing error: {exc}")
        flash(f"Processing error: {exc}", "error")
        return redirect(url_for("main.upload_page"))


@main_bp.route("/delete_meeting/<int:meeting_id>", methods=["POST"])
def delete_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    db.session.delete(meeting)
    db.session.commit()
    flash(f"'{meeting.title}' deleted.", "success")
    return redirect(url_for("main.past_meetings"))


@main_bp.route("/export/<int:meeting_id>")
def export_pdf(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    try:
        pdf_path = create_meeting_minutes_pdf(meeting)
        return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path))
    except Exception as exc:
        flash(f"PDF export error: {exc}", "error")
        return redirect(url_for("main.view_results", meeting_id=meeting_id))


# ── JSON APIs ─────────────────────────────────────────────────────────────────

@main_bp.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.get_json() or {}
    meeting = Meeting.query.get_or_404(data.get("meeting_id"))
    answer = chat_with_meeting_context(meeting.original_transcript, data.get("question", ""))
    return jsonify({"answer": answer})


@main_bp.route("/api/meetings")
def api_meetings():
    meetings = Meeting.query.order_by(Meeting.date_created.desc()).all()
    return jsonify([
        {
            "id": m.id,
            "title": m.title,
            "type": m.meeting_type,
            "date": m.date_created.isoformat(),
            "sentiment": m.sentiment,
            "action_items": m.total_count,
            "done": m.done_count,
            "completion_rate": m.completion_rate,
        }
        for m in meetings
    ])


@main_bp.route("/api/action-items/<int:item_id>", methods=["PATCH"])
def update_action_item(item_id):
    item = ActionItem.query.get_or_404(item_id)
    data = request.get_json() or {}
    for field in ("status", "owner", "due_date", "priority", "notes"):
        if field in data:
            setattr(item, field, data[field])
    item.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(item.to_dict())


@main_bp.route("/api/action-items", methods=["POST"])
def create_action_item():
    data = request.get_json() or {}
    meeting = Meeting.query.get_or_404(data.get("meeting_id"))
    item = ActionItem(
        meeting_id=meeting.id,
        task=data.get("task", "New task"),
        owner=data.get("owner", "Unassigned"),
        due_date=data.get("due_date", "TBD"),
        priority=data.get("priority", "Medium"),
        status=data.get("status", "Open"),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@main_bp.route("/api/meetings/<int:meeting_id>/share", methods=["POST"])
def generate_share_link(meeting_id):
    """Generate (or return existing) public share token for a meeting."""
    meeting = Meeting.query.get_or_404(meeting_id)
    token = meeting.generate_share_token()
    db.session.commit()
    share_url = url_for("main.share_meeting", token=token, _external=True)
    return jsonify({"token": token, "url": share_url})


@main_bp.route("/api/meetings/<int:meeting_id>/share", methods=["DELETE"])
def revoke_share_link(meeting_id):
    """Revoke the public share link."""
    meeting = Meeting.query.get_or_404(meeting_id)
    meeting.share_token = None
    db.session.commit()
    return jsonify({"revoked": True})


@main_bp.route("/api/recipes", methods=["POST"])
def create_recipe():
    """Create a custom user recipe."""
    data = request.get_json() or {}
    recipe = Recipe(
        name=data.get("name", "My Recipe"),
        icon=data.get("icon", "bi-stars"),
        description=data.get("description", ""),
        prompt_template=data.get("prompt_template", ""),
        is_builtin=False,
    )
    db.session.add(recipe)
    db.session.commit()
    return jsonify(recipe.to_dict()), 201


@main_bp.route("/api/recipes/<int:recipe_id>", methods=["DELETE"])
def delete_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.is_builtin:
        return jsonify({"error": "Cannot delete built-in recipes"}), 403
    db.session.delete(recipe)
    db.session.commit()
    return jsonify({"deleted": True})


@main_bp.route("/api/recipes/<int:recipe_id>/run", methods=["POST"])
def run_recipe(recipe_id):
    """Execute a recipe against a specific meeting's transcript."""
    recipe = Recipe.query.get_or_404(recipe_id)
    data = request.get_json() or {}
    meeting = Meeting.query.get_or_404(data.get("meeting_id"))
    result = apply_recipe(recipe.prompt_template, meeting.original_transcript)
    return jsonify({"result": result, "recipe_name": recipe.name})


@main_bp.route("/api/transcribe-chunk", methods=["POST"])
def transcribe_chunk():
    """Transcribe a live-recorded audio chunk (WebM blob from MediaRecorder)."""
    audio = request.files.get("audio")
    if not audio:
        return jsonify({"error": "No audio provided"}), 400

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"chunk_{uuid.uuid4().hex}.webm"
    filepath = os.path.join(upload_dir, filename)
    audio.save(filepath)

    transcript = transcribe_audio(filepath)
    os.remove(filepath)
    return jsonify({"transcript": transcript})
