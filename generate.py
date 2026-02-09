#!/usr/bin/env python3
"""
generate.py

Generates `projectNNNN.html` files at the repository root from
`projectTEMPLATE.html` and the contents of `projects/<id>/`.

Behavior:
- For each folder under `projects/` (e.g. `0050`) create or replace
  `project0050.html` in the repo root.
- Any existing `projectNNNN.html` in the repo root that does NOT match a
  folder under `projects/` will be deleted.

Usage:
  python3 generate.py

This script is intentionally simple and avoids external dependencies.
"""

from pathlib import Path
import re
import shutil
import html


ROOT = Path(__file__).parent
PROJECTS_DIR = ROOT / "projects"
TEMPLATE_PATH = ROOT / "projectTEMPLATE.html"


def read_text(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def make_trailer_html(folder: Path) -> str:
    # look for trailer.* (gif, mp4, webm, jpg, png)
    for ext in (".mp4", ".webm", ".gif", ".jpg", ".jpeg", ".png"):
        for p in folder.glob(f"trailer*{ext}"):
            rel = f"projects/{folder.name}/{p.name}"
            if ext in (".mp4", ".webm"):
                return f'<video class="project-trailer" muted loop playsinline src="{rel}"></video>'
            else:
                return f'<img class="project-trailer" src="{rel}" alt="trailer" />'
    return ""


def make_images_html(folder: Path) -> str:
    imgs = []
    # include image*. and icon.* as available
    for pattern in ("icon.*", "image*.*"):
        for p in sorted(folder.glob(pattern)):
            if p.is_file():
                rel = f"projects/{folder.name}/{p.name}"
                alt = html.escape(p.stem)
                imgs.append(f"<img src=\"{rel}\" alt=\"{alt}\" />")
    return "\n".join(imgs)


def make_nav_html(ids, idx):
    prev_html = ""
    next_html = ""
    if idx > 0:
        prev_id = ids[idx - 1]
        prev_html = f'<a class="nav-prev" href="project{prev_id}.html">◀ Prev</a>'
    if idx < len(ids) - 1:
        next_id = ids[idx + 1]
        next_html = f'<a class="nav-next" href="project{next_id}.html">Next ▶</a>'
    if prev_html or next_html:
        return f'<nav class="project-nav">{prev_html} {next_html}</nav>'
    return ""


def make_also_like_html(ids, current_id):
    blocks = []
    for pid in ids:
        if pid == current_id:
            continue
        icon = ROOT / "projects" / pid / "icon.png"
        if not icon.exists():
            # try common extensions
            for ext in (".jpg", ".jpeg", ".gif", ".svg"):
                if (ROOT / "projects" / pid / ("icon" + ext)).exists():
                    icon = ROOT / "projects" / pid / ("icon" + ext)
                    break
        if icon.exists():
            rel = f"projects/{pid}/{icon.name}"
            blocks.append(f'<a class="also-like-project" href="project{pid}.html"><img class="also-like-img" src="{rel}"/></a>')
        else:
            blocks.append(f'<a class="also-like-project" href="project{pid}.html">{pid}</a>')
    if not blocks:
        return ""
    return f'<section class="also-like-section"><div class="also-like-container">{"".join(blocks)}</div></section>'


def generate_for(folder: Path, ids: list, idx: int, template: str) -> str:
    pid = folder.name
    title = html.escape(read_text(folder / "title.txt")) or ""
    desc_raw = read_text(folder / "description.txt") or ""
    desc = html.escape(desc_raw).replace("\n", "<br />")
    trailer = make_trailer_html(folder)
    images = make_images_html(folder)
    nav = make_nav_html(ids, idx)
    also_like = make_also_like_html(ids, pid)

    out = template.replace("{{PROJECT_NUM}}", pid)
    out = out.replace("{{TITLE}}", title)
    out = out.replace("{{DESC}}", desc)
    out = out.replace("{{TRAILER}}", trailer)
    out = out.replace("{{IMAGES}}", images)
    out = out.replace("{{NAV}}", nav)
    out = out.replace("{{ALSO_LIKE}}", also_like)
    return out


def update_index_html(ids: list):
    """Replace the project grid in index.html to reflect `ids`.

    Keeps the rest of index.html intact when possible.
    """
    index_path = ROOT / "index.html"
    if not index_path.exists():
        print("index.html not found; skipping index update")
        return

    html_text = index_path.read_text(encoding="utf-8")

    # build anchors
    anchors = []
    for pid in ids:
        anchors.append(
            f"        <a class=\"project\" data-project=\"{pid}\" data-hashtags=\"\" href=\"project{pid}.html\">\n"
            f"          <img src=\"projects/{pid}/icon.svg\" alt=\"icon\" class=\"project-logo\" />\n"
            f"          <span class=\"project-label\">{pid}</span>\n"
            f"        </a>\n\n"
        )

    anchors_html = "".join(anchors)

    # replace inner content of <div class="grid" id="projectGrid">...</div>
    grid_re = re.compile(r'(<div class="grid" id="projectGrid">)(.*?)(</div>)', re.DOTALL)
    if grid_re.search(html_text):
        new_html = grid_re.sub(r"\1\n" + anchors_html + r"      \3", html_text)
        index_path.write_text(new_html, encoding="utf-8")
        print("Updated index.html project grid")
    else:
        print("Could not find project grid in index.html; skipping update")


def main():
    if not PROJECTS_DIR.exists():
        print(f"projects/ folder not found: {PROJECTS_DIR}")
        return

    # load template
    if TEMPLATE_PATH.exists():
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
    else:
        print("projectTEMPLATE.html not found; aborting")
        return

    # gather project ids (folders)
    ids = [p.name for p in sorted(PROJECTS_DIR.iterdir()) if p.is_dir()]
    if not ids:
        print("No project folders found in projects/")
        return

    # generate each projectNNNN.html (create or replace)
    for idx, pid in enumerate(ids):
        folder = PROJECTS_DIR / pid
        out_html = generate_for(folder, ids, idx, template)
        target = ROOT / f"project{pid}.html"
        target.write_text(out_html, encoding="utf-8")
        print(f"WROTE {target.name}")

    # delete any projectNNNN.html files in root that don't match ids
    pattern = re.compile(r'^project(\d{3,}).html$')
    for p in ROOT.iterdir():
        if not p.is_file():
            continue
        m = pattern.match(p.name)
        if m:
            pid = m.group(1)
            if pid not in ids and p.name != TEMPLATE_PATH.name:
                try:
                    p.unlink()
                    print(f"DELETED {p.name}")
                except Exception as e:
                    print(f"FAILED to delete {p.name}: {e}")

    # update index.html grid to match current projects
    update_index_html(ids)

    print("Done.")


if __name__ == '__main__':
    main()

