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
    from reportlab.graphics import renderSVG
    from reportlab.graphics.barcode import qr
    from reportlab.graphics.shapes import Drawing
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
QR_ASSET = REPO_ROOT / "assets" / "qr" / "bagaturiya.svg"
PORTFOLIO_IMAGE_DIR = REPO_ROOT / "assets" / "portfolio-images"
TITLE_PAGE_IMAGE = REPO_ROOT / "assets" / "titlepageimage" / "titlepagemage.png"

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
    media_names: list[str]
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


def project_skills(folder: Path, fallback: Iterable[str]) -> list[str]:
    """Read display/ranking skills from the editable per-project skill.txt file."""
    path = folder / "skill.txt"
    if not path.exists():
        return dedupe(fallback)
    raw = read_text(path)
    hashtag_values = re.findall(r"#[\w-]+", raw, flags=re.UNICODE)
    if hashtag_values:
        return dedupe(hashtag_values)
    return dedupe(re.split(r"[,;\n]+", raw))


def project_year(folder: Path, configured: Any) -> str:
    year = clean_text(configured)
    if year:
        return year
    match = re.search(r"\b(?:19|20)\d{2}\b", read_text(folder / "titledescription.txt"))
    return match.group(0) if match else ""


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


def discover_media(folder: Path) -> list[str]:
    """Return ordered image and numbered text media, excluding project metadata."""
    def sort_key(path: Path) -> tuple[int, str]:
        match = re.search(r"(\d+)", path.stem)
        return (int(match.group(1)) if match else 999999, path.name.lower())

    metadata_stems = {
        "_readme", "description", "hashtags", "skill", "title",
        "titledescription", "trailer",
    }
    media = [
        path for path in folder.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS | {".txt"}
        and path.stem.lower() not in metadata_stems | {"icon"}
    ]
    return [path.name for path in sorted(media, key=sort_key)]


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
                year=project_year(folder, extra.get("year", "")),
                tags=dedupe([*site_tags, *extra.get("tags", [])]),
                software=dedupe(extra.get("software", [])),
                skills=project_skills(folder, extra.get("skills", [])),
                priority=float(extra.get("priority", 0)),
                media_names=discover_media(folder),
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
        image_paths = [
            project.folder / name
            for name in project.media_names
            if (project.folder / name).suffix.lower() in IMAGE_EXTENSIONS
        ]
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


def ensure_qr_asset() -> Path:
    """Create a deterministic vector QR code without adding another dependency."""
    if QR_ASSET.exists():
        return QR_ASSET
    QR_ASSET.parent.mkdir(parents=True, exist_ok=True)
    widget = qr.QrCodeWidget("https://bagaturiya.com")
    x1, y1, x2, y2 = widget.getBounds()
    size = 96
    drawing = Drawing(size, size, transform=[size / (x2 - x1), 0, 0, size / (y2 - y1), 0, 0])
    drawing.add(widget)
    renderSVG.drawToFile(drawing, str(QR_ASSET))
    return QR_ASSET


def portfolio_image_asset(
    project: Project,
    source: Path,
    variant: str,
    max_pixels: int,
) -> Path:
    """Create a compact, print-ready derivative while preserving source files."""
    safe_stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", source.stem).strip("-") or "image"
    destination = PORTFOLIO_IMAGE_DIR / project.project_id / f"{safe_stem}-{variant}.jpg"
    if destination.exists() and destination.stat().st_mtime >= source.stat().st_mtime:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as original:
        original.seek(0)
        image = ImageOps.exif_transpose(original).convert("RGBA")
        background = Image.new("RGBA", image.size, "white")
        background.alpha_composite(image)
        flattened = background.convert("RGB")
        flattened.thumbnail((max_pixels, max_pixels), Image.Resampling.LANCZOS)
        flattened.save(destination, "JPEG", quality=83, optimize=True, progressive=True)
    return destination


def body_image_groups(values: list[Path]) -> list[list[Path]]:
    """Group body images so the final page is single and the prior page is paired."""
    if not values:
        return []
    if len(values) <= 2:
        return [values]

    final_image = values[-1:]
    earlier = values[:-1]
    groups: list[list[Path]] = []
    if len(earlier) % 2:
        groups.append(earlier[:1])
        earlier = earlier[1:]
    groups.extend(
        earlier[index:index + 2]
        for index in range(0, len(earlier), 2)
    )
    groups.append(final_image)
    return groups


def is_areal_archive(project: Project) -> bool:
    return project.project_id == "0010" or normalize(project.title) == "areal archive"


def build_portfolio_html(
    html_destination: Path,
    cv: dict[str, Any],
    application: dict[str, Any],
    selected: list[RankedProject],
    full_portfolio: bool = False,
) -> str:
    template = PORTFOLIO_TEMPLATE.read_text(encoding="utf-8")
    stylesheet = PORTFOLIO_CSS.read_text(encoding="utf-8")
    qr_asset = ensure_qr_asset()
    portrait_folder = published_project_folders().get("2409")
    fallback_portrait = (portrait_folder or PROJECTS_DIR / "2409") / "image1.png"
    cover_image = TITLE_PAGE_IMAGE if TITLE_PAGE_IMAGE.exists() else fallback_portrait
    name = clean_text(cv["name"])
    portfolio_label = "Full portfolio" if full_portfolio else "Tailored portfolio"
    office = clean_text(application.get("office", ""))
    position = clean_text(application.get("position", ""))
    if full_portfolio:
        cover_sentence = f"This is the full portfolio of {name}."
    else:
        target = " - ".join(value for value in (office, position) if value)
        cover_sentence = f"This tailored portfolio was prepared for {target or 'this application'}."

    def page_chrome(page_number: int, inverse: bool = False) -> str:
        modifier = " page-chrome--inverse" if inverse else ""
        return f'''<div class="page-chrome{modifier}" aria-hidden="true">
        <span class="page-corner page-corner--tl"></span>
        <span class="page-corner page-corner--tr"></span>
        <span class="page-corner page-corner--bl"></span>
        <span class="page-corner page-corner--br"></span>
        <span class="page-number">{page_number:02d}</span>
      </div>'''

    def project_media(project: Project) -> list[Path]:
        return [
            project.folder / name
            for name in project.media_names
            if (project.folder / name).exists()
        ]

    def content_page_count(project: Project) -> int:
        body_media = project_media(project)[1:]
        if is_areal_archive(project):
            return 1 if body_media else 0
        return len(body_image_groups(body_media))

    def cv_list(values: Iterable[str], class_name: str = "cv-card-list") -> str:
        items = "".join(
            f"<li>{html.escape(clean_text(value))}</li>"
            for value in values if clean_text(value)
        )
        return f'<ul class="{class_name}">{items}</ul>' if items else ""

    def cv_card(number: str, title: str, body: str, modifier: str = "") -> str:
        classes = f"cv-card {modifier}".strip()
        return f'''<section class="{classes}">
        <p class="cv-card-number">{html.escape(number)}</p>
        <h2>{html.escape(title)}</h2>
        {body}
      </section>'''

    contact_rows: list[str] = []
    contact_icons = {
        "phone": REPO_ROOT / "assets" / "icons" / "phone.svg",
        "email": REPO_ROOT / "assets" / "icons" / "email.svg",
        "linkedin": REPO_ROOT / "assets" / "icons" / "linkedin.svg",
        "instagram": REPO_ROOT / "assets" / "icons" / "instagram.svg",
        "location": REPO_ROOT / "assets" / "icons" / "location.svg",
    }
    for key in ("phone", "email", "website", "linkedin", "instagram", "location"):
        value = clean_text(cv.get("contact", {}).get(key, ""))
        if not value:
            continue
        if key == "phone":
            href = "tel:" + re.sub(r"[^+0-9]", "", value)
        elif key == "email":
            href = f"mailto:{value}"
        elif key == "location":
            href = "https://www.google.com/maps/search/?api=1&query=" + value.replace(" ", "+")
        else:
            href = value if value.startswith(("http://", "https://")) else f"https://{value}"
        icon_path = contact_icons.get(key)
        if icon_path and icon_path.exists():
            icon = f'<img src="{portfolio_asset_url(icon_path, html_destination)}" alt="" />'
        else:
            icon = '''<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10.6 13.4a1 1 0 0 1 0-1.4l3.4-3.4a3 3 0 1 1 4.2 4.2l-2 2a3 3 0 0 1-4.2 0 1 1 0 1 1 1.4-1.4 1 1 0 0 0 1.4 0l2-2a1 1 0 0 0-1.4-1.4L12 13.4a1 1 0 0 1-1.4 0ZM13.4 10.6a1 1 0 0 1 0 1.4L10 15.4a3 3 0 1 1-4.2-4.2l2-2a3 3 0 0 1 4.2 0 1 1 0 1 1-1.4 1.4 1 1 0 0 0-1.4 0l-2 2A1 1 0 0 0 8.6 14l3.4-3.4a1 1 0 0 1 1.4 0Z"/></svg>'''
        external = ' target="_blank" rel="noopener noreferrer"' if key not in {"phone", "email"} else ""
        contact_rows.append(
            f'''<a class="cv-contact-row" href="{html.escape(href, quote=True)}"{external}>
          <span class="cv-contact-icon">{icon}</span>
          <span class="cv-contact-value">{html.escape(value)}</span>
        </a>'''
        )

    education_entries: list[str] = []
    for entry in cv.get("education", []):
        professors = entry.get("professors", [])
        professor_markup = ""
        if professors:
            professor_markup = (
                '<div class="cv-professors"><span>Professors</span>'
                + cv_list(professors, "cv-inline-list")
                + "</div>"
            )
        education_entries.append(f'''<article class="cv-education-entry">
          <header><h3>{html.escape(clean_text(entry.get("qualification", "")))}</h3><time>{html.escape(clean_text(entry.get("dates", "")))}</time></header>
          <p>{html.escape(clean_text(entry.get("institution", "")))}</p>
          {professor_markup}
        </article>''')

    experience_entries: list[str] = []
    for entry in cv.get("experience", []):
        company = clean_text(entry.get("company", ""))
        location = clean_text(entry.get("location", ""))
        institution = " - ".join(value for value in (company, location) if value)
        experience_entries.append(f'''<article class="cv-experience-entry">
          <header><h3>{html.escape(clean_text(entry.get("role", "")))}</h3><time>{html.escape(clean_text(entry.get("dates", "")))}</time></header>
          <p>{html.escape(institution)}</p>
          {cv_list(entry.get("highlights", []))}
        </article>''')

    skill_groups = "".join(
        f'''<article class="cv-skill-group">
          <h3>{html.escape(clean_text(group.get("name", "Skills")))}</h3>
          <div class="cv-mini-chips">{"".join(f'<span>{html.escape(clean_text(value))}</span>' for value in group.get("items", []))}</div>
        </article>'''
        for group in cv.get("skill_groups", [])
    )
    hobby_groups = "".join(
        f'''<article class="cv-hobby-group">
          <h3>{html.escape(clean_text(category.get("name", "Interests")))}</h3>
          {cv_list(category.get("items", []))}
        </article>'''
        for category in cv.get("hobbies", {}).get("categories", [])
    )
    language_chips = "".join(
        f'<span>{html.escape(clean_text(language))}</span>'
        for language in cv.get("languages", [])
    )

    profile_card = cv_card(
        "02",
        "Profile",
        f'<p class="cv-profile-text">{html.escape(clean_text(cv.get("profile_en") or cv.get("profile", "")))}</p>',
        "cv-profile-card",
    )
    contact_card = cv_card(
        "01", "Contact", f'<div class="cv-contact-list">{"".join(contact_rows)}</div>', "cv-contact-card"
    )
    language_card = cv_card(
        "07", "Languages", f'<div class="cv-language-list">{language_chips}</div>', "cv-language-card"
    )
    education_card = cv_card(
        "03", "Education", f'<div class="cv-education-list">{"".join(education_entries)}</div>', "cv-education-card"
    )
    experience_card = cv_card(
        "04", "Experience", f'<div class="cv-experience-list">{"".join(experience_entries)}</div>', "cv-experience-card"
    )
    skills_card = cv_card("05", "Skills & software", skill_groups, "cv-skills-card")
    hobbies_card = cv_card(
        "06", "Interests & achievements", f'<div class="cv-hobby-grid">{hobby_groups}</div>', "cv-hobbies-card"
    )

    cv_page_one = f'''<section class="portfolio-page cv-document-page cv-document-page--one">
      <div class="cv-page-one-grid">
        <figure class="cv-portrait-card"><img src="{portfolio_asset_url(fallback_portrait, html_destination)}" alt="Portrait of {html.escape(name)}" /></figure>
        {profile_card}
        {contact_card}
        {language_card}
        {education_card}
        {experience_card}
      </div>
      {page_chrome(2)}
    </section>'''
    cv_page_two = f'''<section class="portfolio-page cv-document-page cv-document-page--two">
      <div class="cv-page-two-grid">{skills_card}{hobbies_card}</div>
      {page_chrome(3)}
    </section>'''

    def media_caption(path: Path) -> str:
        return path.stem

    def text_media_markup(path: Path, modifier: str) -> str:
        raw = read_text(path)
        raw = re.sub(r"-\s*\n\s*", "", raw)
        paragraphs = [clean_text(value) for value in re.split(r"\n\s*\n", raw) if clean_text(value)]
        body = "".join(f"<p>{html.escape(value)}</p>" for value in paragraphs)
        return f'<div class="text-media text-media--{modifier}"><div>{body}</div></div>'

    def media_markup(project: Project, path: Path, variant: str, max_pixels: int) -> str:
        if path.suffix.lower() == ".txt":
            return text_media_markup(path, variant)
        asset = portfolio_image_asset(project, path, variant, max_pixels)
        return f'<img src="{portfolio_asset_url(asset, html_destination)}" alt="{html.escape(media_caption(path))}" />'

    project_start_pages: dict[str, int] = {}
    next_page = 5
    for item in selected:
        project_start_pages[item.project.project_id] = next_page
        next_page += 1 + content_page_count(item.project)

    cover = f'''<section class="portfolio-page cover">
      <div class="cover-copy">
        <p class="cover-initials">{html.escape(clean_text(cv.get("initials", "")))}</p>
        <h1>{html.escape(clean_text(cv["name"]))}</h1>
        <p class="cover-headline">{html.escape(clean_text(cv.get("headline", "")))}</p>
        <p class="cover-target"><span>{html.escape(portfolio_label)}</span>{html.escape(cover_sentence)}</p>
      </div>
      <figure class="cover-image"><img src="{portfolio_asset_url(cover_image, html_destination)}" alt="Portrait of {html.escape(name)}" /></figure>
      {page_chrome(1)}
    </section>'''

    contents_items = "".join(
        f'''<li><span>{html.escape(item.project.title)}</span>
        <span>{project_start_pages[item.project.project_id]:02d}</span></li>'''
        for item in selected
    )
    contents = f'''<section class="portfolio-page contents-page">
      <div class="contents-list">
        <h2>Selected projects</h2>
        <ol>{contents_items}</ol>
      </div>
      <div class="contents-frame"><span>portfolio</span></div>
      {page_chrome(4)}
    </section>'''

    project_pages: list[str] = []
    for index, item in enumerate(selected, start=1):
        project = item.project
        page_number = project_start_pages[project.project_id]
        media_paths = project_media(project)
        lead_path = media_paths[0] if media_paths else None
        lead_media = media_markup(project, lead_path, "title", 1800) if lead_path else '<div class="project-media-empty">Media forthcoming</div>'
        lead_caption = html.escape(media_caption(lead_path)) if lead_path else ""
        year = project.year or "Year forthcoming"
        skills = project.skills or [f"#{tag}" for tag in project.tags[:5]]
        project_pages.append(f'''<section class="portfolio-page project-title-page">
      <figure class="project-title-image">{lead_media}<figcaption>{lead_caption}</figcaption></figure>
      <div class="project-title-copy">
        <div>
          <p class="project-number">{project.project_id} / {index:02d}</p>
          <h2>{html.escape(project.title)}</h2>
          <p class="project-year">{html.escape(year)}</p>
          <p class="project-description">{html.escape(project.description or "Project description forthcoming.")}</p>
        </div>
        <div class="project-skills">
          <p class="section-label">Skills used</p>
          <div class="chips">{portfolio_chips(skills, "chip--outline")}</div>
        </div>
      </div>
      {page_chrome(page_number)}
    </section>''')

        if is_areal_archive(project):
            body_media = media_paths[1:]
            if body_media:
                columns = max(1, round((len(body_media) * 297 / 210) ** 0.5))
                rows = max(1, (len(body_media) + columns - 1) // columns)
                remainder = len(body_media) % columns
                last_row_spans: list[int] = []
                if remainder:
                    base_span, extra_spans = divmod(columns, remainder)
                    last_row_spans = [
                        base_span + (1 if index < extra_spans else 0)
                        for index in range(remainder)
                    ]
                grid_markup: list[str] = []
                last_row_start = len(body_media) - remainder if remainder else len(body_media)
                for offset, path in enumerate(body_media):
                    span = ""
                    if remainder and offset >= last_row_start:
                        span_value = last_row_spans[offset - last_row_start]
                        span = f' style="grid-column:span {span_value}"'
                    grid_markup.append(
                        f'''<figure{span}>{media_markup(project, path, "grid", 620)}
                  <figcaption>{html.escape(media_caption(path))}</figcaption></figure>'''
                    )
                grid_items = "".join(grid_markup)
                project_pages.append(f'''<section class="portfolio-page areal-grid-page">
      <div class="areal-grid" style="--grid-columns:{columns};--grid-rows:{rows}">{grid_items}</div>
      {page_chrome(page_number + 1, inverse=True)}
    </section>''')
            continue

        groups = body_image_groups(media_paths[1:])
        for group_index, group in enumerate(groups):
            figures: list[str] = []
            for path in group:
                figures.append(f'''<figure class="content-figure" data-caption="{html.escape(media_caption(path), quote=True)}">
          <div class="content-image">{media_markup(project, path, "content", 1600)}</div>
          <figcaption>{html.escape(media_caption(path))}</figcaption>
        </figure>''')
            content_number = page_number + 1 + group_index
            page_modifier = " project-content-page--single" if len(group) == 1 else ""
            single_caption = (
                f'\n      <div class="single-page-caption">{html.escape(media_caption(group[0]))}</div>'
                if len(group) == 1 else ""
            )
            project_pages.append(f'''<section class="portfolio-page project-content-page{page_modifier}">
      <div class="project-content-grid" data-count="{len(group)}">{"".join(figures)}</div>{single_caption}
      {page_chrome(content_number)}
    </section>''')

    closing_page_number = next_page
    closing = f'''<section class="portfolio-page closing-page">
      <a class="closing-link" href="https://bagaturiya.com">
        <img src="{portfolio_asset_url(qr_asset, html_destination)}" alt="QR code linking to bagaturiya.com" />
        <span>Want to see more?</span>
        <strong>go to bagaturiya.com</strong>
      </a>
      {page_chrome(closing_page_number)}
    </section>'''

    title = f"{clean_text(cv['name'])} - {'Full Portfolio' if full_portfolio else 'Portfolio'}"
    if full_portfolio:
        styles = '<link rel="stylesheet" href="portfolio-export/templates/portfolio.css" />'
    else:
        styles = f"<style>{stylesheet}</style>"
    return (template
            .replace("{{DOCUMENT_TITLE}}", html.escape(title))
            .replace("{{PORTFOLIO_STYLES}}", styles)
            .replace("{{FAVICON_URL}}", portfolio_asset_url(REPO_ROOT / "assets" / "favicon" / "favicon.svg", html_destination))
            .replace("{{COVER}}", cover)
            .replace("{{CONTENTS}}", cv_page_one + cv_page_two + contents)
            .replace("{{PROJECTS}}", "\n".join(project_pages))
            .replace("{{CLOSING}}", closing))


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
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--no-first-run",
                "--no-pdf-header-footer",
                "--allow-file-access-from-files",
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=10000",
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
        build_portfolio_html(
            html_destination,
            cv,
            application,
            selected,
            full_portfolio,
        ),
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
    render_cv(cv_path, cv_data, prepared, selected)
    render_portfolio(
        portfolio_path,
        cv_data,
        prepared,
        selected,
        html_destination=portfolio_html_path,
    )
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
