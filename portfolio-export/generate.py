#!/usr/bin/env python3
"""Generate a tailored portfolio and CV from the existing static-site library."""

from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from PIL import Image, ImageOps
    from reportlab.lib.colors import Color, HexColor, black, white
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas
except ImportError as exc:
    raise SystemExit(
        "Missing export dependencies. Run: "
        "python3 -m pip install -r portfolio-export/requirements.txt"
    ) from exc


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PROJECTS_DIR = REPO_ROOT / "projects"
DATA_DIR = SCRIPT_DIR / "data"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output" / "pdf"
PORTFOLIO_TEMPLATE = SCRIPT_DIR / "templates" / "portfolio.html"
PORTFOLIO_CSS = SCRIPT_DIR / "templates" / "portfolio.css"

ACCENT = HexColor("#ff5a1f")
INK = HexColor("#101010")
MID = HexColor("#5c5c5c")
LIGHT = HexColor("#efefed")
PAPER = HexColor("#fafaf7")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "our", "that", "the", "their",
    "this", "to", "we", "will", "with", "you", "your", "looking", "strong",
    "experience", "skills", "role", "position", "work", "working", "office",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
PROJECT_FOLDER_PATTERN = re.compile(
    r"^(?P<project_id>\d{4,})(?:-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*))?$"
)


@dataclass
class Project:
    project_id: str
    folder: Path
    title: str
    description: str
    website_tags: list[str]
    year: str
    tags: list[str]
    software: list[str]
    skills: list[str]
    priority: float
    image_names: list[str]
    exclude: bool


@dataclass
class RankedProject:
    project: Project
    score: float
    reasons: list[str]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def clean_text(value: Any) -> str:
    text = str(value or "")
    replacements = {
        "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2026": "...",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean_text(value).lower()).strip()


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = clean_text(value)
        key = normalize(cleaned)
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def dedupe_vocabulary(values: Iterable[str]) -> list[str]:
    """Dedupe known terms while treating simple singular/plural forms alike."""
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = clean_text(value)
        key = normalize(cleaned)
        if key.endswith("s"):
            key = key[:-1]
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalize(value)).strip("-")
    return slug or "application"


def website_hashtags(folder: Path) -> list[str]:
    raw = read_text(folder / "hashtags.txt")
    return [match.lower().lstrip("#") for match in re.findall(r"#\w+", raw)]


def published_project_folders() -> dict[str, Path]:
    projects: dict[str, Path] = {}
    invalid: list[str] = []
    for folder in PROJECTS_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        match = PROJECT_FOLDER_PATTERN.fullmatch(folder.name)
        if match is None:
            if folder.name[:1].isdigit():
                invalid.append(folder.name)
            continue
        project_id = match.group("project_id")
        if project_id in projects:
            raise ValueError(
                f"Duplicate project ID {project_id}: "
                f"{projects[project_id].name} and {folder.name}"
            )
        projects[project_id] = folder
    if invalid:
        raise ValueError(
            "Invalid project folder name(s): " + ", ".join(sorted(invalid))
            + ". Use NNNN-lowercase-hyphenated-title."
        )
    return projects


def discover_images(folder: Path) -> list[str]:
    def sort_key(path: Path) -> tuple[int, str]:
        match = re.search(r"(\d+)", path.stem)
        return (int(match.group(1)) if match else 999999, path.name.lower())

    images = [
        path for path in folder.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
        and path.stem.lower().startswith("image")
    ]
    return [path.name for path in sorted(images, key=sort_key)]


def load_projects() -> list[Project]:
    overrides = load_json(DATA_DIR / "projects.json")
    projects: list[Project] = []
    folders = published_project_folders()
    for project_id in sorted(folders, key=int, reverse=True):
        folder = folders[project_id]
        extra = overrides.get(project_id, {})
        site_tags = website_hashtags(folder)
        projects.append(
            Project(
                project_id=project_id,
                folder=folder,
                title=clean_text(read_text(folder / "title.txt") or folder.name),
                description=clean_text(read_text(folder / "description.txt")),
                website_tags=site_tags,
                year=clean_text(extra.get("year", "")),
                tags=dedupe([*site_tags, *extra.get("tags", [])]),
                software=dedupe(extra.get("software", [])),
                skills=dedupe(extra.get("skills", [])),
                priority=float(extra.get("priority", 0)),
                image_names=extra.get("images", []) or discover_images(folder),
                exclude=bool(extra.get("exclude", False)),
            )
        )
    return projects


def load_application(path: Path, args: argparse.Namespace) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        application = load_json(path)
    else:
        application = {"job_description": read_text(path)}

    overrides = {
        "office": args.office,
        "position": args.position,
        "software": split_csv(args.software),
        "skills": split_csv(args.skills),
        "focus": split_csv(args.focus),
        "project_limit": args.project_limit,
        "include_hobbies": args.include_hobbies,
        "hobby_categories": split_csv(args.hobby_categories),
    }
    for key, value in overrides.items():
        if value not in (None, [], ""):
            application[key] = value

    application.setdefault("office", path.stem.replace("-", " ").title())
    application.setdefault("position", "Architecture position")
    application.setdefault("job_description", "")
    application.setdefault("software", [])
    application.setdefault("skills", [])
    application.setdefault("focus", [])
    application.setdefault("project_limit", 4)
    application.setdefault("include_projects", [])
    application.setdefault("exclude_projects", [])
    application.setdefault("include_hobbies", True)
    application.setdefault("hobby_categories", [])
    application.setdefault("hobby_item_limit", 5)
    return application


def meaningful_tokens(value: Any) -> set[str]:
    return {
        token for token in normalize(value).split()
        if len(token) >= 4 and token not in STOPWORDS
    }


def enrich_application(
    application: dict[str, Any], projects: list[Project], cv: dict[str, Any]
) -> dict[str, Any]:
    """Detect known software/skills/focus phrases in pasted vacancy text."""
    job_text = normalize(
        f"{application.get('position', '')} {application.get('job_description', '')}"
    )
    software_groups = [
        group for group in cv.get("skill_groups", [])
        if normalize(group.get("name", "")) == "software"
    ]
    cv_software = [item for group in software_groups for item in group.get("items", [])]
    cv_skills = [
        item
        for group in cv.get("skill_groups", [])
        if normalize(group.get("name", "")) != "software"
        for item in group.get("items", [])
    ]
    known = {
        "software": dedupe_vocabulary([
            *(item for project in projects for item in project.software),
            *cv_software,
        ]),
        "skills": dedupe_vocabulary([
            *(item for project in projects for item in project.skills),
            *cv_skills,
        ]),
        "focus": dedupe_vocabulary(item for project in projects for item in project.tags),
    }
    inferred: dict[str, list[str]] = {}
    for key, vocabulary in known.items():
        detected = [item for item in vocabulary if normalize(item) in job_text]
        existing = application.get(key, [])
        application[key] = dedupe([*existing, *detected])
        existing_normalized = {normalize(item) for item in existing}
        inferred[key] = [item for item in detected if normalize(item) not in existing_normalized]
    application["inferred_from_job_text"] = inferred
    return application


def phrase_matches(wanted: Iterable[str], available: Iterable[str]) -> list[str]:
    available_normalized = {normalize(item) for item in available}
    return [clean_text(item) for item in wanted if normalize(item) in available_normalized]


def rank_projects(projects: list[Project], application: dict[str, Any]) -> list[RankedProject]:
    structured_text = " ".join(
        clean_text(item)
        for key in ("software", "skills", "focus")
        for item in application.get(key, [])
    )
    job_tokens = meaningful_tokens(
        f"{application.get('position', '')} {application.get('job_description', '')} {structured_text}"
    )
    included = {str(item) for item in application.get("include_projects", [])}
    excluded = {str(item) for item in application.get("exclude_projects", [])}
    ranked: list[RankedProject] = []

    for project in projects:
        if project.exclude or project.project_id in excluded:
            continue
        score = project.priority
        reasons: list[str] = []
        if project.priority:
            reasons.append(f"library priority +{project.priority:g}")

        software_matches = phrase_matches(application.get("software", []), project.software)
        skill_matches = phrase_matches(application.get("skills", []), project.skills)
        focus_matches = phrase_matches(application.get("focus", []), project.tags)
        if software_matches:
            points = 10 * len(software_matches)
            score += points
            reasons.append(f"software: {', '.join(software_matches)} +{points:g}")
        if skill_matches:
            points = 6 * len(skill_matches)
            score += points
            reasons.append(f"skills: {', '.join(skill_matches)} +{points:g}")
        if focus_matches:
            points = 5 * len(focus_matches)
            score += points
            reasons.append(f"focus: {', '.join(focus_matches)} +{points:g}")

        project_text = " ".join(
            [project.title, project.description, *project.tags, *project.software, *project.skills]
        )
        token_matches = sorted(job_tokens & meaningful_tokens(project_text))
        if token_matches:
            points = min(len(token_matches), 8)
            score += points
            reasons.append(f"keywords: {', '.join(token_matches[:8])} +{points:g}")
        if "selected" in [normalize(tag) for tag in project.website_tags]:
            score += 1
            reasons.append("website #selected +1")
        if project.project_id in included:
            score += 1000
            reasons.append("explicitly included +1000")
        ranked.append(RankedProject(project=project, score=score, reasons=reasons))

    return sorted(ranked, key=lambda item: (-item.score, -item.project.priority, item.project.project_id))


def wrap_lines(text: str, font: str, size: float, max_width: float, max_lines: int | None = None) -> list[str]:
    words = clean_text(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or stringWidth(candidate, font, size) <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = word
        if max_lines and len(lines) >= max_lines:
            break
    if current and (not max_lines or len(lines) < max_lines):
        lines.append(current)
    if max_lines and len(lines) == max_lines and words:
        while lines[-1] and stringWidth(lines[-1] + "...", font, size) > max_width:
            lines[-1] = lines[-1][:-1].rstrip()
        if not lines[-1].endswith("..."):
            lines[-1] += "..."
    return lines


def draw_text_block(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font: str = "Helvetica",
    size: float = 10,
    leading: float | None = None,
    color: Color = INK,
    max_lines: int | None = None,
) -> float:
    leading = leading or size * 1.35
    pdf.setFillColor(color)
    pdf.setFont(font, size)
    lines = wrap_lines(text, font, size, max_width, max_lines=max_lines)
    for line in lines:
        pdf.drawString(x, y, line)
        y -= leading
    return y


def draw_label(pdf: canvas.Canvas, text: str, x: float, y: float, color: Color = MID) -> None:
    pdf.setFillColor(color)
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(x, y, clean_text(text).upper())


def draw_chips(
    pdf: canvas.Canvas,
    values: Iterable[str],
    x: float,
    y: float,
    max_width: float,
    fill: Color = LIGHT,
    text_color: Color = INK,
    max_rows: int = 3,
) -> float:
    start_x = x
    row = 1
    for value in dedupe(values):
        label = clean_text(value)
        width = stringWidth(label, "Helvetica", 7.5) + 13
        if x + width > start_x + max_width:
            row += 1
            if row > max_rows:
                break
            x = start_x
            y -= 17
        pdf.setFillColor(fill)
        pdf.roundRect(x, y - 9, width, 14, 7, fill=1, stroke=0)
        pdf.setFillColor(text_color)
        pdf.setFont("Helvetica", 7.5)
        pdf.drawString(x + 6.5, y - 5, label)
        x += width + 5
    return y - 18


def prepared_image(path: Path, target_ratio: float) -> ImageReader:
    with Image.open(path) as source:
        source.seek(0)
        image = ImageOps.exif_transpose(source).convert("RGB")
        source_ratio = image.width / image.height
        if source_ratio > target_ratio:
            crop_width = int(image.height * target_ratio)
            left = (image.width - crop_width) // 2
            image = image.crop((left, 0, left + crop_width, image.height))
        else:
            crop_height = int(image.width / target_ratio)
            top = (image.height - crop_height) // 2
            image = image.crop((0, top, image.width, top + crop_height))
        image.thumbnail((2200, 2200), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=91, optimize=True)
        buffer.seek(0)
        return ImageReader(buffer)


def draw_image_cover(pdf: canvas.Canvas, path: Path, x: float, y: float, width: float, height: float) -> bool:
    if not path.exists() or path.suffix.lower() not in IMAGE_EXTENSIONS:
        return False
    try:
        pdf.drawImage(
            prepared_image(path, width / height), x, y,
            width=width, height=height, preserveAspectRatio=False, mask="auto",
        )
        return True
    except Exception as exc:  # Keep one bad source image from blocking the export.
        print(f"Warning: could not render {path}: {exc}", file=sys.stderr)
        return False


def draw_footer(pdf: canvas.Canvas, name: str, page_number: int, width: float, color: Color = MID) -> None:
    pdf.setStrokeColor(HexColor("#d8d8d4"))
    pdf.setLineWidth(0.4)
    pdf.line(30, 24, width - 30, 24)
    pdf.setFillColor(color)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(30, 12, clean_text(name))
    pdf.drawRightString(width - 30, 12, f"{page_number:02d}")


def render_portfolio_reportlab(
    destination: Path,
    cv: dict[str, Any],
    application: dict[str, Any],
    selected: list[RankedProject],
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = landscape(A4)
    pdf = canvas.Canvas(str(destination), pagesize=(page_width, page_height), pageCompression=1)
    pdf.setTitle(f"{cv['name']} - Portfolio - {application['office']}")
    pdf.setAuthor(cv["name"])

    # Cover
    pdf.setFillColor(INK)
    pdf.rect(0, 0, page_width, page_height, fill=1, stroke=0)
    portrait_folder = published_project_folders().get("2409")
    portrait = (portrait_folder or PROJECTS_DIR / "2409") / "image1.png"
    image_x = page_width * 0.61
    if draw_image_cover(pdf, portrait, image_x, 0, page_width - image_x, page_height):
        pdf.setFillColor(Color(0, 0, 0, alpha=0.28))
        pdf.rect(image_x, 0, page_width - image_x, page_height, fill=1, stroke=0)
    pdf.setFillColor(ACCENT)
    pdf.rect(40, page_height - 54, 48, 4, fill=1, stroke=0)
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, page_height - 78, clean_text(cv.get("initials", "")))
    pdf.setFont("Helvetica-Bold", 31)
    pdf.drawString(40, page_height - 152, clean_text(cv["name"]))
    pdf.setFont("Helvetica", 16)
    pdf.drawString(40, page_height - 178, clean_text(cv.get("headline", "")))
    pdf.setFillColor(HexColor("#bdbdbd"))
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, 76, "TAILORED PORTFOLIO")
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(40, 54, clean_text(application.get("position", "")))
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, 37, clean_text(application.get("office", "")))
    pdf.showPage()

    # Project pages
    for index, item in enumerate(selected, start=1):
        project = item.project
        pdf.setFillColor(PAPER)
        pdf.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        left_x = 30
        left_width = 235
        media_x = 286
        media_width = page_width - media_x - 30
        media_height = page_height - 60
        image_paths = [project.folder / name for name in project.image_names]
        image_paths = [path for path in image_paths if path.exists()][:2]

        if len(image_paths) >= 2:
            gap = 8
            block_height = (media_height - gap) / 2
            draw_image_cover(pdf, image_paths[0], media_x, 30 + block_height + gap, media_width, block_height)
            draw_image_cover(pdf, image_paths[1], media_x, 30, media_width, block_height)
        elif image_paths:
            draw_image_cover(pdf, image_paths[0], media_x, 30, media_width, media_height)
        else:
            pdf.setFillColor(LIGHT)
            pdf.rect(media_x, 30, media_width, media_height, fill=1, stroke=0)
            pdf.setFillColor(MID)
            pdf.setFont("Helvetica", 9)
            pdf.drawCentredString(media_x + media_width / 2, page_height / 2, "No portfolio image selected")

        pdf.setFillColor(ACCENT)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left_x, page_height - 38, f"{project.project_id} / {index:02d}")
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 23)
        title_lines = wrap_lines(project.title, "Helvetica-Bold", 23, left_width, max_lines=2)
        y = page_height - 82
        for line in title_lines:
            pdf.drawString(left_x, y, line)
            y -= 27
        if project.year:
            pdf.setFillColor(MID)
            pdf.setFont("Helvetica", 9)
            pdf.drawString(left_x, y - 1, project.year)
            y -= 24

        y = draw_chips(pdf, project.tags[:7], left_x, y, left_width, max_rows=3)
        y -= 4
        draw_label(pdf, "Project", left_x, y)
        y -= 17
        y = draw_text_block(
            pdf, project.description or "Project description not yet available.",
            left_x, y, left_width, size=8.8, leading=12.2, max_lines=15,
        )
        y -= 8
        if project.software:
            draw_label(pdf, "Software", left_x, y)
            y -= 16
            y = draw_chips(pdf, project.software, left_x, y, left_width, fill=INK, text_color=white, max_rows=2)
        draw_footer(pdf, cv["name"], index + 1, page_width)
        pdf.showPage()

    pdf.save()


def portfolio_asset_url(path: Path, html_destination: Path) -> str:
    """Return a repo-relative URL so generated HTML remains portable."""
    return os.path.relpath(path, html_destination.parent).replace(os.sep, "/")


def portfolio_chips(values: Iterable[str], modifier: str = "") -> str:
    class_name = f"chip {modifier}".strip()
    return "".join(
        f'<span class="{class_name}">{html.escape(clean_text(value))}</span>'
        for value in dedupe(values)
    )


def build_portfolio_html(
    html_destination: Path,
    cv: dict[str, Any],
    application: dict[str, Any],
    selected: list[RankedProject],
    full_portfolio: bool = False,
) -> str:
    template = PORTFOLIO_TEMPLATE.read_text(encoding="utf-8")
    stylesheet = PORTFOLIO_CSS.read_text(encoding="utf-8")
    portrait_folder = published_project_folders().get("2409")
    portrait = (portrait_folder or PROJECTS_DIR / "2409") / "image1.png"
    portfolio_label = "FULL PORTFOLIO" if full_portfolio else "TAILORED PORTFOLIO"
    position = "Selected works" if full_portfolio else clean_text(application.get("position", ""))
    office = f"{len(selected)} projects" if full_portfolio else clean_text(application.get("office", ""))
    cover = f'''<section class="portfolio-page cover">
      <div class="cover-copy">
        <div class="cover-mark"></div>
        <p class="cover-initials">{html.escape(clean_text(cv.get("initials", "")))}</p>
        <h1>{html.escape(clean_text(cv["name"]))}</h1>
        <p class="cover-headline">{html.escape(clean_text(cv.get("headline", "")))}</p>
        <div class="cover-target">
          <p class="cover-label">{portfolio_label}</p>
          <p class="cover-position">{html.escape(position)}</p>
          <p class="cover-office">{html.escape(office)}</p>
        </div>
      </div>
      <div class="cover-image"><img src="{portfolio_asset_url(portrait, html_destination)}" alt="" /></div>
      <footer class="page-footer"><span>{html.escape(clean_text(cv["name"]))}</span><span>01</span></footer>
    </section>'''

    project_pages: list[str] = []
    for index, item in enumerate(selected, start=1):
        project = item.project
        image_paths = [project.folder / name for name in project.image_names]
        image_paths = [path for path in image_paths if path.exists()][:2]
        if image_paths:
            media = "".join(
                f'<img src="{portfolio_asset_url(path, html_destination)}" alt="" />'
                for path in image_paths
            )
        else:
            media = '<div class="project-media-empty">No portfolio image selected</div>'
        year = f'<p class="project-year">{html.escape(project.year)}</p>' if project.year else ""
        software = ""
        if project.software:
            software = f'''<div class="software">
          <p class="section-label">Software</p>
          <div class="chips">{portfolio_chips(project.software, "chip--dark")}</div>
        </div>'''
        project_pages.append(f'''<section class="portfolio-page project-page">
      <div class="project-copy">
        <p class="project-number">{project.project_id} / {index:02d}</p>
        <h2>{html.escape(project.title)}</h2>
        {year}
        <div class="chips">{portfolio_chips(project.tags[:7])}</div>
        <p class="section-label">Project</p>
        <p class="project-description">{html.escape(project.description or "Project description not yet available.")}</p>
        {software}
      </div>
      <div class="project-media" data-count="{len(image_paths)}">{media}</div>
      <footer class="page-footer"><span>{html.escape(clean_text(cv["name"]))}</span><span>{index + 1:02d}</span></footer>
    </section>''')

    title = f"{clean_text(cv['name'])} - {'Full Portfolio' if full_portfolio else 'Portfolio'}"
    if full_portfolio:
        styles = '<link rel="stylesheet" href="portfolio-export/templates/portfolio.css" />'
    else:
        styles = f"<style>{stylesheet}</style>"
    return (template
            .replace("{{DOCUMENT_TITLE}}", html.escape(title))
            .replace("{{PORTFOLIO_STYLES}}", styles)
            .replace("{{COVER}}", cover)
            .replace("{{PROJECTS}}", "\n".join(project_pages)))


def chrome_executable() -> str | None:
    candidates = [
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    return next((str(path) for path in candidates if path and Path(path).exists()), None)


def print_html_to_pdf(source: Path, destination: Path) -> bool:
    browser = chrome_executable()
    if not browser:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="portfolio-chrome-") as profile:
        process = subprocess.Popen(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--disable-breakpad",
                "--disable-extensions",
                "--no-first-run",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile}",
                f"--print-to-pdf={destination}",
                source.resolve().as_uri(),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 90
        previous_size = -1
        stable_checks = 0
        success = False
        while time.monotonic() < deadline:
            if destination.exists() and destination.stat().st_size > 1000:
                size = destination.stat().st_size
                stable_checks = stable_checks + 1 if size == previous_size else 0
                previous_size = size
                if stable_checks >= 4:
                    success = True
                    break
            if process.poll() is not None:
                success = destination.exists() and destination.stat().st_size > 1000
                break
            time.sleep(.25)
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    if not success:
        print("Warning: browser PDF export did not complete.", file=sys.stderr)
    return success


def render_portfolio(
    destination: Path,
    cv: dict[str, Any],
    application: dict[str, Any],
    selected: list[RankedProject],
    html_destination: Path | None = None,
    full_portfolio: bool = False,
) -> Path:
    """Render portfolio HTML from the shared template, then print that HTML to PDF."""
    html_destination = html_destination or destination.with_suffix(".html")
    html_destination.parent.mkdir(parents=True, exist_ok=True)
    html_destination.write_text(
        build_portfolio_html(html_destination, cv, application, selected, full_portfolio),
        encoding="utf-8",
    )
    if not print_html_to_pdf(html_destination, destination):
        print("Warning: falling back to the legacy ReportLab portfolio renderer.", file=sys.stderr)
        render_portfolio_reportlab(destination, cv, application, selected)
    return html_destination


def generate_full_portfolio() -> tuple[Path, Path]:
    """Generate the canonical public portfolio containing every publishable project."""
    cv_data = load_json(DATA_DIR / "cv.json")
    projects = [project for project in load_projects() if not project.exclude]
    selected = [RankedProject(project=project, score=0, reasons=[]) for project in projects]
    html_path = REPO_ROOT / "portfolio.html"
    pdf_path = REPO_ROOT / "assets" / "downloads" / "Ivan_Bagaturiya_Portfolio.pdf"
    render_portfolio(
        pdf_path,
        cv_data,
        {"office": "", "position": ""},
        selected,
        html_destination=html_path,
        full_portfolio=True,
    )
    return html_path, pdf_path


def skill_relevance(group: dict[str, Any], application: dict[str, Any]) -> tuple[int, list[str]]:
    target_text = normalize(
        " ".join([
            application.get("job_description", ""),
            *application.get("software", []),
            *application.get("skills", []),
            *application.get("focus", []),
        ])
    )
    ordered = sorted(
        group.get("items", []),
        key=lambda item: (normalize(item) not in target_text, group.get("items", []).index(item)),
    )
    score = sum(1 for item in ordered if normalize(item) in target_text)
    return score, ordered


def selected_hobbies(cv: dict[str, Any], application: dict[str, Any]) -> list[tuple[str, str]]:
    if not application.get("include_hobbies"):
        return []
    hobby_data = cv.get("hobbies", {})
    categories = hobby_data.get("categories", [])
    requested = {normalize(item) for item in application.get("hobby_categories", [])}
    if requested:
        categories = [category for category in categories if normalize(category.get("name", "")) in requested]
    limit = max(1, int(application.get("hobby_item_limit", 5)))
    selected_count = 0
    chosen: dict[str, list[str]] = {
        clean_text(category.get("name", "Interessen")): [] for category in categories
    }
    depth = 0
    while selected_count < limit:
        added = False
        for category in categories:
            items = category.get("items", [])
            if depth < len(items):
                name = clean_text(category.get("name", "Interessen"))
                chosen[name].append(clean_text(items[depth]))
                selected_count += 1
                added = True
                if selected_count >= limit:
                    break
        if not added:
            break
        depth += 1
    return [
        (name, item)
        for name, items in chosen.items()
        for item in items
    ]


def render_cv(
    destination: Path,
    cv: dict[str, Any],
    application: dict[str, Any],
    selected: list[RankedProject],
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = A4
    pdf = canvas.Canvas(str(destination), pagesize=A4, pageCompression=1)
    pdf.setTitle(f"{cv['name']} - CV - {application['office']}")
    pdf.setAuthor(cv["name"])
    margin = 34

    pdf.setFillColor(INK)
    pdf.rect(0, page_height - 152, page_width, 152, fill=1, stroke=0)
    pdf.setFillColor(ACCENT)
    pdf.rect(margin, page_height - 40, 42, 4, fill=1, stroke=0)
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawString(margin, page_height - 78, clean_text(cv["name"]))
    pdf.setFont("Helvetica", 11)
    pdf.drawString(margin, page_height - 99, clean_text(cv.get("headline", "")))
    pdf.setFillColor(HexColor("#bdbdbd"))
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(margin, page_height - 125, "TARGET")
    pdf.setFillColor(white)
    pdf.setFont("Helvetica", 8.5)
    pdf.drawString(
        margin, page_height - 141,
        clean_text(f"{application.get('position', '')} - {application.get('office', '')}"),
    )

    left_x = margin
    left_width = 320
    right_x = 382
    right_width = page_width - margin - right_x
    y_left = page_height - 184
    y_right = y_left

    draw_label(pdf, "Profile", left_x, y_left)
    y_left -= 20
    y_left = draw_text_block(
        pdf, cv.get("profile", ""), left_x, y_left, left_width,
        size=9.3, leading=13.2, max_lines=9,
    )

    groups = []
    for group in cv.get("skill_groups", []):
        score, items = skill_relevance(group, application)
        groups.append((score, group.get("name", "Skills"), items))
    groups.sort(key=lambda item: -item[0])
    y_left -= 18
    draw_label(pdf, "Relevant skills", left_x, y_left)
    y_left -= 19
    for _, name, items in groups:
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawString(left_x, y_left, clean_text(name))
        y_left -= 15
        y_left = draw_chips(pdf, items, left_x, y_left, left_width, max_rows=2)
        y_left -= 5

    if cv.get("experience"):
        y_left -= 8
        draw_label(pdf, "Experience", left_x, y_left)
        y_left -= 21
        for entry in cv["experience"]:
            pdf.setFillColor(INK)
            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawString(left_x, y_left, clean_text(entry.get("role", "")))
            pdf.setFont("Helvetica", 8)
            pdf.drawRightString(left_x + left_width, y_left, clean_text(entry.get("dates", "")))
            y_left -= 13
            y_left = draw_text_block(
                pdf, entry.get("company", ""), left_x, y_left, left_width,
                size=8, leading=11, color=MID, max_lines=2,
            )
            y_left -= 11

    draw_label(pdf, "Contact", right_x, y_right)
    y_right -= 20
    contact = cv.get("contact", {})
    for key in ("email", "website", "linkedin", "instagram"):
        value = contact.get(key)
        if not value:
            continue
        pdf.setFillColor(MID)
        pdf.setFont("Helvetica-Bold", 6.8)
        pdf.drawString(right_x, y_right, key.upper())
        y_right -= 11
        y_right = draw_text_block(pdf, value, right_x, y_right, right_width, size=7.8, leading=10, max_lines=2)
        y_right -= 8

    y_right -= 10
    draw_label(pdf, "Education", right_x, y_right)
    y_right -= 20
    for entry in cv.get("education", []):
        y_right = draw_text_block(
            pdf, entry.get("qualification", ""), right_x, y_right, right_width,
            font="Helvetica-Bold", size=8.5, leading=11, max_lines=2,
        )
        y_right = draw_text_block(
            pdf, entry.get("institution", ""), right_x, y_right, right_width,
            size=8, leading=10, color=MID, max_lines=2,
        )
        if entry.get("dates"):
            y_right = draw_text_block(
                pdf, entry["dates"], right_x, y_right, right_width,
                size=7.5, leading=9, color=MID, max_lines=1,
            )
        y_right -= 10

    if cv.get("languages"):
        draw_label(pdf, "Languages", right_x, y_right)
        y_right -= 18
        y_right = draw_chips(pdf, cv["languages"], right_x, y_right, right_width, max_rows=4)

    y_right -= 12
    draw_label(pdf, "Selected work", right_x, y_right)
    y_right -= 20
    for item in selected[:4]:
        project = item.project
        pdf.setFillColor(ACCENT)
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.drawString(right_x, y_right, project.project_id)
        y_right = draw_text_block(
            pdf, project.title, right_x + 32, y_right, right_width - 32,
            font="Helvetica-Bold", size=8, leading=10, max_lines=2,
        )
        pdf.setFillColor(MID)
        pdf.setFont("Helvetica", 7)
        pdf.drawString(right_x + 32, y_right, " / ".join(project.software or project.tags[:2]))
        y_right -= 18

    hobbies = selected_hobbies(cv, application)
    if hobbies and y_right > 72:
        y_right -= 6
        draw_label(pdf, "Interessen", right_x, y_right)
        y_right -= 18
        last_category = ""
        for category, hobby in hobbies:
            if y_right < 52:
                break
            if category != last_category:
                pdf.setFillColor(INK)
                pdf.setFont("Helvetica-Bold", 7.5)
                pdf.drawString(right_x, y_right, category)
                y_right -= 11
                last_category = category
            y_right = draw_text_block(
                pdf, hobby, right_x, y_right, right_width,
                size=7.1, leading=9, color=MID, max_lines=2,
            )
            y_right -= 6

    draw_footer(pdf, cv["name"], 1, page_width)
    pdf.save()


def manifest_data(
    application_source: str | Path,
    application: dict[str, Any],
    selected: list[RankedProject],
    portfolio_path: Path,
    cv_path: Path,
) -> dict[str, Any]:
    return {
        "application_source": str(application_source),
        "application": application,
        "outputs": {"portfolio": str(portfolio_path), "cv": str(cv_path)},
        "selection": [
            {
                "project": item.project.project_id,
                "title": item.project.title,
                "score": round(item.score, 2),
                "reasons": item.reasons,
            }
            for item in selected
        ],
    }


def prepare_application(application: dict[str, Any]) -> dict[str, Any]:
    """Return a complete, isolated application profile for UI and CLI callers."""
    prepared = json.loads(json.dumps(application, ensure_ascii=False))
    prepared.setdefault("office", "Untitled office")
    prepared.setdefault("position", "Architecture position")
    prepared.setdefault("job_description", "")
    prepared.setdefault("software", [])
    prepared.setdefault("skills", [])
    prepared.setdefault("focus", [])
    prepared.setdefault("project_limit", 4)
    prepared.setdefault("include_projects", [])
    prepared.setdefault("exclude_projects", [])
    prepared.setdefault("include_hobbies", True)
    prepared.setdefault("hobby_categories", [])
    prepared.setdefault("hobby_item_limit", 5)
    return prepared


def preview_application(
    application: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[Project], list[RankedProject]]:
    """Enrich an application and rank projects without writing any files."""
    prepared = prepare_application(application)
    cv_data = load_json(DATA_DIR / "cv.json")
    projects = load_projects()
    prepared = enrich_application(prepared, projects, cv_data)
    ranked = rank_projects(projects, prepared)
    return prepared, cv_data, projects, ranked


def generate_application(
    application: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    application_source: str | Path = "local application generator",
) -> dict[str, Any]:
    """Generate one tailored package and return its manifest."""
    prepared, cv_data, _projects, ranked = preview_application(application)
    if not ranked:
        raise ValueError("No publishable projects are available for this application.")

    project_limit = max(1, min(int(prepared.get("project_limit", 4)), len(ranked)))
    selected = ranked[:project_limit]
    target_slug = slugify(f"{prepared['office']} {prepared['position']}")
    target_dir = output_dir.resolve() / target_slug
    target_dir.mkdir(parents=True, exist_ok=True)
    portfolio_path = target_dir / "Ivan_Bagaturiya_Portfolio.pdf"
    portfolio_html_path = target_dir / "Ivan_Bagaturiya_Portfolio.html"
    cv_path = target_dir / "Ivan_Bagaturiya_CV.pdf"
    manifest_path = target_dir / "selection.json"
    application_path = target_dir / "application.json"

    application_path.write_text(
        json.dumps(prepared, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    render_portfolio(
        portfolio_path,
        cv_data,
        prepared,
        selected,
        html_destination=portfolio_html_path,
    )
    render_cv(cv_path, cv_data, prepared, selected)
    manifest = manifest_data(
        application_source, prepared, selected, portfolio_path, cv_path
    )
    manifest["outputs"]["application"] = str(application_path)
    manifest["outputs"]["portfolio_html"] = str(portfolio_html_path)
    manifest["outputs"]["selection"] = str(manifest_path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a tailored PDF portfolio and CV from the existing project library."
    )
    parser.add_argument("application", type=Path, help="Application JSON or plain-text vacancy")
    parser.add_argument("--office")
    parser.add_argument("--position")
    parser.add_argument("--software", help="Comma-separated software")
    parser.add_argument("--skills", help="Comma-separated skills")
    parser.add_argument("--focus", help="Comma-separated focus areas")
    parser.add_argument("--project-limit", type=int)
    hobby_group = parser.add_mutually_exclusive_group()
    hobby_group.add_argument("--include-hobbies", dest="include_hobbies", action="store_true")
    hobby_group.add_argument("--no-hobbies", dest="include_hobbies", action="store_false")
    parser.set_defaults(include_hobbies=None)
    parser.add_argument("--hobby-categories", help="Comma-separated hobby categories")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    application_path = args.application.resolve()
    if not application_path.exists():
        print(f"Application file not found: {application_path}", file=sys.stderr)
        return 2

    application = load_application(application_path, args)
    manifest = generate_application(
        application,
        output_dir=args.output_dir,
        application_source=application_path.resolve(),
    )
    print(f"Portfolio: {manifest['outputs']['portfolio']}")
    print(f"CV: {manifest['outputs']['cv']}")
    print(f"Selection: {manifest['outputs']['selection']}")
    print(
        "Selected projects: "
        + ", ".join(item["project"] for item in manifest["selection"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
