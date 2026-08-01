#!/usr/bin/env python3
"""Generate the comprehensive public CV download from data/cv.json."""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any, Iterable

try:
    from reportlab.lib import colors
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        KeepTogether,
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError as exc:
    raise SystemExit(
        "Missing PDF dependencies. Run: python3 -m pip install -r "
        "portfolio-export/requirements.txt"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
CV_PATH = Path(__file__).resolve().parent / "data" / "cv.json"
DEFAULT_OUTPUT = ROOT / "assets" / "downloads" / "Ivan_Bagaturiya_CV.pdf"
INK = HexColor("#11110f")
MUTED = HexColor("#64635f")
LINE = HexColor("#d7d4cc")
ACCENT = HexColor("#ff5a1f")
PAPER = HexColor("#fffef9")


def load_cv() -> dict[str, Any]:
    with CV_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def clean(value: Any) -> str:
    return escape(str(value or "").strip())


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle(
            "Name", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=27, leading=28, textColor=colors.white, spaceAfter=5,
        ),
        "headline": ParagraphStyle(
            "Headline", parent=base["Normal"], fontName="Helvetica",
            fontSize=10, leading=13, textColor=HexColor("#c8c7c2"),
        ),
        "contact": ParagraphStyle(
            "Contact", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.6, leading=10.5, textColor=colors.white, alignment=TA_RIGHT,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=12, leading=15, textColor=INK, spaceBefore=12, spaceAfter=8,
            borderColor=ACCENT, borderWidth=0, borderPadding=0,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.5, leading=12.2, textColor=INK, spaceAfter=5,
        ),
        "body_muted": ParagraphStyle(
            "BodyMuted", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.8, leading=10.5, textColor=MUTED, spaceAfter=5,
        ),
        "entry_title": ParagraphStyle(
            "EntryTitle", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=9.4, leading=11.5, textColor=INK,
        ),
        "date": ParagraphStyle(
            "Date", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.5, leading=10, textColor=ACCENT, alignment=TA_RIGHT,
        ),
        "label": ParagraphStyle(
            "Label", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.2, leading=9.5, textColor=MUTED, spaceAfter=3,
        ),
        "chip": ParagraphStyle(
            "Chip", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.6, leading=10.5, textColor=INK,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.8, leading=10.8, textColor=INK, leftIndent=0,
        ),
    }


def section_heading(title: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [
        Table(
            [["", Paragraph(clean(title).upper(), styles["section"])]],
            colWidths=[4 * mm, 166 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), ACCENT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 8),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]),
        ),
        Spacer(1, 2 * mm),
    ]


def bullet_list(values: Iterable[str], styles: dict[str, ParagraphStyle]) -> ListFlowable:
    return ListFlowable(
        [
            ListItem(Paragraph(clean(value), styles["bullet"]), leftIndent=7)
            for value in values if value
        ],
        bulletType="bullet",
        start="circle",
        leftIndent=10,
        bulletFontName="Helvetica",
        bulletFontSize=4,
        bulletColor=ACCENT,
        spaceAfter=4,
    )


def page_footer(pdf, document, name: str) -> None:
    pdf.saveState()
    pdf.setTitle(f"{name} - Curriculum Vitae")
    pdf.setAuthor(name)
    width, _height = A4
    pdf.setStrokeColor(LINE)
    pdf.setLineWidth(0.4)
    pdf.line(20 * mm, 13 * mm, width - 20 * mm, 13 * mm)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 6.7)
    pdf.drawString(20 * mm, 8.5 * mm, name)
    pdf.drawRightString(width - 20 * mm, 8.5 * mm, f"{document.page:02d}")
    pdf.restoreState()


def build_public_cv(destination: Path) -> None:
    cv = load_cv()
    styles = make_styles()
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(destination), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=17 * mm, bottomMargin=19 * mm,
        title=f"{cv.get('name', '')} - Curriculum Vitae",
        author=cv.get("name", ""),
    )
    story: list[Any] = []

    contact = cv.get("contact", {})
    contact_lines = [
        contact.get("location"), contact.get("phone"), contact.get("email"),
        contact.get("website"), contact.get("linkedin"), contact.get("instagram"),
    ]
    header = Table(
        [[
            [
                Paragraph(clean(cv.get("name")), styles["name"]),
                Paragraph(clean(cv.get("headline_de") or cv.get("headline")), styles["headline"]),
            ],
            Paragraph("<br/>".join(clean(item) for item in contact_lines if item), styles["contact"]),
        ]],
        colWidths=[105 * mm, 65 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), INK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ]),
    )
    story.extend([header, Spacer(1, 7 * mm)])

    story.extend(section_heading("Profile", styles))
    if cv.get("profile_en"):
        story.append(Paragraph(f'<font color="#ff5a1f"><b>EN</b></font> &nbsp; {clean(cv["profile_en"])}', styles["body"]))
    german_profile = cv.get("profile_de") or cv.get("profile")
    if german_profile:
        story.append(Paragraph(f'<font color="#ff5a1f"><b>DE</b></font> &nbsp; {clean(german_profile)}', styles["body"]))

    story.extend(section_heading("Skills and software", styles))
    skill_rows = []
    for group in cv.get("skill_groups", []):
        skill_rows.append([
            Paragraph(clean(group.get("name", "Skills")), styles["label"]),
            Paragraph(" · ".join(clean(item) for item in group.get("items", [])), styles["chip"]),
        ])
    if skill_rows:
        story.append(Table(
            skill_rows, colWidths=[43 * mm, 127 * mm],
            style=TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEABOVE", (0, 0), (-1, -1), 0.35, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]),
        ))

    story.extend(section_heading("Experience", styles))
    for entry in cv.get("experience", []):
        company = clean(entry.get("company"))
        if entry.get("location"):
            company += f" · {clean(entry['location'])}"
        entry_content = [
            Table(
                [[
                    Paragraph(clean(entry.get("role")), styles["entry_title"]),
                    Paragraph(clean(entry.get("dates")), styles["date"]),
                ]],
                colWidths=[132 * mm, 38 * mm],
                style=TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]),
            ),
            Paragraph(company, styles["body_muted"]),
            bullet_list(entry.get("highlights", []), styles),
            Spacer(1, 2.2 * mm),
        ]
        story.append(KeepTogether(entry_content))

    story.extend(section_heading("Education", styles))
    for entry in cv.get("education", []):
        education_content = [
            Table(
                [[
                    Paragraph(clean(entry.get("qualification")), styles["entry_title"]),
                    Paragraph(clean(entry.get("dates")), styles["date"]),
                ]],
                colWidths=[132 * mm, 38 * mm],
                style=TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]),
            ),
            Paragraph(clean(entry.get("institution")), styles["body_muted"]),
        ]
        professors = entry.get("professors", [])
        if professors:
            education_content.append(Paragraph(
                "<b>Professors:</b> " + " · ".join(clean(item) for item in professors),
                styles["body"],
            ))
        education_content.append(Spacer(1, 3 * mm))
        story.append(KeepTogether(education_content))

    story.extend(section_heading("Languages", styles))
    story.append(Paragraph(" · ".join(clean(item) for item in cv.get("languages", [])), styles["body"]))

    story.extend(section_heading("Interests and achievements", styles))
    for category in cv.get("hobbies", {}).get("categories", []):
        story.append(KeepTogether([
            Paragraph(clean(category.get("name", "Interests")), styles["entry_title"]),
            bullet_list(category.get("items", []), styles),
            Spacer(1, 2 * mm),
        ]))

    document.build(
        story,
        onFirstPage=lambda pdf, doc: page_footer(pdf, doc, cv.get("name", "")),
        onLaterPages=lambda pdf, doc: page_footer(pdf, doc, cv.get("name", "")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the public comprehensive CV PDF.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_public_cv(args.output.resolve())
    print(f"Public CV: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
