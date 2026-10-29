"""Generate a clean A4 CV PDF from editable database content."""
from __future__ import annotations
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether

NAVY = colors.HexColor("#15264a")
BLUE = colors.HexColor("#4361ee")
MUTED = colors.HexColor("#65718b")
TEXT = colors.HexColor("#202a3b")


def _clean(value) -> str:
    return str(value or "").strip()

def _paragraph(value: str, style):
    return Paragraph(escape(value).replace("\n", "<br/>"), style)

def generate_cv_pdf(cv: dict, settings: dict, education: list[dict], skills: list[dict], projects: list[dict]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm, title=f"{settings.get('cv_name', 'CV')} - CV", author=settings.get('cv_name', 'CV'))
    base = getSampleStyleSheet()
    name_style = ParagraphStyle("CVName", parent=base["Title"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=colors.white, alignment=TA_LEFT, spaceAfter=4)
    head_style = ParagraphStyle("CVHead", parent=base["Normal"], fontName="Helvetica", fontSize=10, leading=14, textColor=colors.HexColor("#e5eaff"))
    section_style = ParagraphStyle("CVSection", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=BLUE, spaceBefore=10, spaceAfter=4, keepWithNext=True)
    body_style = ParagraphStyle("CVBody", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=TEXT, spaceAfter=3)
    item_style = ParagraphStyle("CVItem", parent=body_style, leftIndent=7, firstLineIndent=-7, bulletIndent=0, spaceAfter=3)
    muted_style = ParagraphStyle("CVMuted", parent=body_style, fontSize=8, leading=11, textColor=MUTED)
    story = []
    name = _clean(settings.get("cv_name")) or "Ahmed Chai"
    headline = _clean(cv.get("headline"))
    contact = [
        _clean(cv.get("email") or settings.get("contact_email")),
        _clean(cv.get("phone")),
        _clean(cv.get("location") or settings.get("location")),
    ]
    contact = [x for x in contact if x]
    top_lines = [headline] if headline else []
    if contact:
        top_lines.append("  |  ".join(contact))
    else:
        top_lines.append("Contact details not added yet")
    header = Table([[Paragraph(escape(name), name_style)], [Paragraph(escape("\n".join(top_lines)), head_style)]], colWidths=[174*mm])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY), ("LEFTPADDING", (0,0), (-1,-1), 12), ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,0), 11), ("BOTTOMPADDING", (0,-1), (-1,-1), 11), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.extend([header, Spacer(1, 4*mm)])

    def section(title: str, rows: list):
        if rows:
            story.append(Paragraph(escape(title.upper()), section_style))
            story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#e4e9f2"), spaceAfter=5))
            story.extend(rows)

    summary = _clean(cv.get("summary"))
    if summary and not summary.lower().startswith("add a verified"):
        section("Professional Summary", [_paragraph(summary, body_style)])
    education_rows = []
    for item in education:
        data = item.get("data", {})
        inst = _clean(data.get("institution") or data.get("title"))
        if not inst:
            continue
        qualification = _clean(data.get("qualification"))
        if qualification.lower().startswith("add verified"):
            qualification = ""
        dates = _clean(data.get("dates"))
        desc = _clean(data.get("description"))
        if desc.lower().startswith("education details can be completed"):
            desc = ""
        detail = " | ".join(x for x in [qualification, dates] if x)
        education_rows.append(KeepTogether([Paragraph(f"<b>{escape(inst)}</b>", body_style)] + ([ _paragraph(detail, muted_style) ] if detail else []) + ([ _paragraph(desc, body_style) ] if desc else [])))
    section("Education", education_rows)
    skill_names = [_clean(x.get("data", {}).get("title")) for x in skills if _clean(x.get("data", {}).get("title"))]
    if skill_names:
        section("Skills", [_paragraph("  ·  ".join(skill_names), body_style)])
    project_rows = []
    for item in projects:
        data = item.get("data", {})
        title = _clean(data.get("title"))
        if not title:
            continue
        desc = _clean(data.get("description"))
        tech = _clean(data.get("technologies"))
        project_rows.append(KeepTogether([Paragraph(f"<b>{escape(title)}</b>", body_style)] + ([_paragraph(desc, body_style)] if desc else []) + ([_paragraph("Technologies: " + tech, muted_style)] if tech else [])))
    section("Selected Projects", project_rows)
    for field, title in [("work_experience", "Experience"), ("certifications", "Certifications"), ("achievements", "Achievements"), ("additional_information", "Additional Information")]:
        value = _clean(cv.get(field))
        rows = [_paragraph(line.strip().lstrip("-•* "), item_style) for line in value.splitlines() if line.strip()]
        section(title, rows)
    if not any([summary and not summary.lower().startswith("add a verified"), skill_names, project_rows, any(_clean(cv.get(k)) for k in ("work_experience", "certifications", "achievements", "additional_information"))]):
        story.extend([Spacer(1, 4*mm), Paragraph("Complete the editable summary, contact details, skills, and experience in the Admin dashboard before submitting this CV.", muted_style)])
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e4e9f2")))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("Editable CV template · Review all details for accuracy before use", muted_style))
    doc.build(story)
    return buffer.getvalue()
