"""
PDF generation module for Convoq.
Creates professional meeting minutes PDFs using ReportLab.
"""

import os
from datetime import datetime

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BLUE = colors.HexColor("#1e40af")
LIGHT_BLUE = colors.HexColor("#f1f5f9")
GRID = colors.HexColor("#e2e8f0")
STRIPE = colors.HexColor("#f8fafc")
RED = colors.HexColor("#dc2626")
AMBER = colors.HexColor("#d97706")
GREEN = colors.HexColor("#16a34a")


def create_meeting_minutes_pdf(meeting, output_path=None):
    if not output_path:
        safe_title = "".join(
            c for c in meeting.title if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        date_str = meeting.date_created.strftime("%Y%m%d_%H%M")
        filename = f"convoq_{safe_title}_{date_str}.pdf".replace(" ", "_")
        output_path = os.path.join(
            current_app.root_path, "static", "downloads", filename
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=60,
        leftMargin=60,
        topMargin=60,
        bottomMargin=60,
    )

    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"],
        fontSize=22, spaceAfter=4, alignment=TA_CENTER,
        textColor=BLUE,
    )
    subtitle_style = ParagraphStyle(
        "Sub", parent=styles["Normal"],
        fontSize=11, spaceAfter=24, alignment=TA_CENTER,
        textColor=colors.grey,
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"],
        fontSize=13, spaceAfter=8, spaceBefore=18,
        textColor=BLUE, borderPad=2,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, spaceAfter=5, leftIndent=12,
    )
    risk_style = ParagraphStyle(
        "Risk", parent=styles["Normal"],
        fontSize=10, spaceAfter=5, leftIndent=12,
        textColor=RED,
    )

    # Title block
    story.append(Paragraph("MEETING MINUTES", title_style))
    story.append(Paragraph("Powered by Convoq AI", subtitle_style))

    # Meta table
    meta = [
        ["Meeting Title:", meeting.title],
        ["Meeting Type:", meeting.meeting_type.title()],
        ["Date & Time:", meeting.date_created.strftime("%d %B %Y  %I:%M %p")],
        ["Sentiment:", meeting.sentiment or "N/A"],
        ["Attendees:", ", ".join(meeting.get_attendees()) or "N/A"],
        ["Keywords:", ", ".join(meeting.get_keywords()[:6]) or "N/A"],
        ["Generated:", datetime.now().strftime("%d %B %Y  %I:%M %p")],
    ]
    meta_table = Table(meta, colWidths=[1.8 * inch, 4.7 * inch])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
        ("TEXTCOLOR", (0, 0), (0, -1), BLUE),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, STRIPE]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)

    # Summary
    if meeting.get_summary():
        story.append(Paragraph("EXECUTIVE SUMMARY", section_style))
        for point in meeting.get_summary():
            story.append(Paragraph(f"• {point}", body_style))

    # Action Items
    action_items = meeting.get_action_items()
    if action_items:
        story.append(Paragraph("ACTION ITEMS", section_style))
        header = [["Task", "Owner", "Due Date", "Priority", "Status"]]
        rows = []
        for item in action_items:
            rows.append([
                item.get("task", ""),
                item.get("owner", "Unassigned"),
                item.get("due_date", "TBD"),
                item.get("priority", "Medium"),
                item.get("status", "Open"),
            ])
        action_table = Table(
            header + rows,
            colWidths=[2.5 * inch, 1.1 * inch, 0.9 * inch, 0.8 * inch, 0.9 * inch],
        )
        action_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, GRID),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, STRIPE]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(action_table)

    # Decisions
    if meeting.get_decisions():
        story.append(Paragraph("KEY DECISIONS", section_style))
        for d in meeting.get_decisions():
            story.append(Paragraph(f"✓  {d}", body_style))

    # Risks
    if meeting.get_risks():
        story.append(Paragraph("RISKS & BLOCKERS", section_style))
        for r in meeting.get_risks():
            story.append(Paragraph(f"⚠  {r}", risk_style))

    # Follow-up email
    if meeting.follow_up_email:
        story.append(Paragraph("FOLLOW-UP EMAIL DRAFT", section_style))
        for line in meeting.follow_up_email.split("\n"):
            story.append(Paragraph(line or " ", body_style))

    # Footer
    story.append(Spacer(1, 24))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=8, alignment=TA_CENTER, textColor=colors.grey,
    )
    story.append(Paragraph(
        f"Generated by Convoq — AI-Powered Meeting Minutes  •  {datetime.now().strftime('%d %b %Y')}",
        footer_style,
    ))

    doc.build(story)
    return output_path
