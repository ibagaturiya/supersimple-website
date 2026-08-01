import json
import os
import re
from html import escape
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECTS_DIR = str(ROOT_DIR / "projects")
OUTPUT_DIR = str(ROOT_DIR)
PROJECT_HTML_DIR = "projecthtml"
PROJECT_TEMPLATE = ROOT_DIR / "templates" / "project.html"
ABOUT_TEMPLATE = ROOT_DIR / "templates" / "about.html"
CV_DATA_PATH = ROOT_DIR / "portfolio-export" / "data" / "cv.json"
PROJECT_FOLDER_PATTERN = re.compile(
    r"^(?P<project_id>\d{4,})(?:-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*))?$"
)


#generates the index.html and project pages based on the contents of the projects folder
#it is neededadd new projects at teh end.


# Copyright HTML (used in both index and project pages)
copyright = '''
<span
  style="
    position: fixed;
    bottom: 2px;
    right: 4px;
    font-size: 9px;
    opacity: 0.35;
    color: #ffffff;
    z-index: 99999;
    pointer-events: none;
  "
>
  created by Ivan Bagaturiya &mdash;
  <script>
    document.write(document.lastModified);
  </script>
</span>
'''

def parse_project_folder(name):
    match = PROJECT_FOLDER_PATTERN.fullmatch(name)
    return match.group("project_id") if match else None

def safe_join(base, *paths):
    base_path = Path(base).resolve()
    final_path = base_path.joinpath(*paths).resolve()
    try:
        final_path.relative_to(base_path)
    except ValueError as exc:
        raise ValueError("Unsafe path detected!") from exc
    return str(final_path)

def discover_project_folders():
    projects = {}
    invalid = []
    for name in os.listdir(PROJECTS_DIR):
        path = Path(safe_join(PROJECTS_DIR, name))
        if not path.is_dir() or name.startswith("_"):
            continue
        project_id = parse_project_folder(name)
        if project_id is None:
            if name[:1].isdigit():
                invalid.append(name)
            continue
        if project_id in projects:
            raise ValueError(
                f"Duplicate project ID {project_id}: {projects[project_id]} and {name}"
            )
        projects[project_id] = name
    if invalid:
        raise ValueError(
            "Invalid project folder name(s): " + ", ".join(sorted(invalid))
            + ". Use NNNN-lowercase-hyphenated-title."
        )
    return projects

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ""

def get_icon(folder):
    for ext in [".svg", ".png", ".jpg", ".jpeg", ".gif"]:
        icon_path = safe_join(folder, f"icon{ext}")
        if os.path.exists(icon_path):
            # compute path relative to where project html files will live
            project_base = os.path.join(OUTPUT_DIR, PROJECT_HTML_DIR)
            return os.path.relpath(icon_path, project_base).replace("\\", "/")
    return ""

def parse_media_number(name):
    base, _ = os.path.splitext(name)
    m = re.match(r'^(\d+)', base)
    if m:
        return int(m.group(1))
    m = re.search(r'image\s*(\d+)', base, re.I)
    return int(m.group(1)) if m else float('inf')


def media_sort_key(name):
    base, _ = os.path.splitext(name)
    m = re.match(r'^(\d+)', base)
    if m:
        return (0, int(m.group(1)), name.lower())
    m = re.search(r'image\s*(\d+)', base, re.I)
    if m:
        return (0, int(m.group(1)), name.lower())
    return (1, float('inf'), name.lower())


def get_media(folder):
    media = []
    exts = {".jpg", ".jpeg", ".gif", ".mp4", ".mp3", ".png", ".pdf", ".txt"}

    try:
        files = os.listdir(folder)
    except FileNotFoundError:
        return media

    for fname in sorted(files, key=media_sort_key):
        base, ext = os.path.splitext(fname)

        # accept numbered files such as 0001_name.jpg, 0002_name.png, or older
        # image1/image00001 style names.
        if ext.lower() in exts and (re.match(r'^\d+', base) or re.search(r'^image\s*\d+$', base, re.I)):
            media_path = safe_join(folder, fname)
            project_base = os.path.join(OUTPUT_DIR, PROJECT_HTML_DIR)
            rel_path = os.path.relpath(media_path, project_base).replace("\\", "/")
            media.append({
                "src": rel_path,
                "number": parse_media_number(fname),
                "name": fname,
            })

    return media

def get_hashtags(folder):
    hashtags_path = safe_join(folder, "hashtags.txt")
    hashtags = read_file(hashtags_path)
    tags = re.findall(r'#\w+', hashtags)
    return [tag.lower() for tag in tags]

def media_html_tag(src):
    if src.lower().endswith(('.jpg', '.jpeg', '.gif', '.png', '.svg')):
        style = ' style="background: transparent;"' if src.lower().endswith('.png') else ''
        return f'<div class="project-media-item"><img class="project-media" src="{src}" alt=""{style} /></div>'
    elif src.lower().endswith('.mp4'):
        return f'<div class="project-media-item"><video class="project-media" src="{src}" controls loop muted playsinline></video></div>'
    elif src.lower().endswith('.mp3'):
        return f'<div class="project-media-item"><audio class="project-media" src="{src}" controls></audio></div>'
    elif src.lower().endswith('.pdf'):
        return f'<div class="project-media-item"><a href="{src}" target="_blank" style="display:block;margin:10px 0;color:#111;font-weight:bold;">View PDF</a></div>'
    elif src.lower().endswith('.txt'):
        # src is relative to projecthtml, for example ../projects/0056-sinuswall/image1.txt
        full_path = os.path.join(OUTPUT_DIR, PROJECT_HTML_DIR, src)
        content = read_file(full_path)
        if content.startswith('http'):
            return f'<div class="project-media-item"><a href="{content}" target="_blank" style="display:block;margin:10px 0;color:#111;font-weight:bold;">View Website</a></div>'
        else:
            return f'<div class="project-media-item"><pre>{content}</pre></div>'  # display as text
    else:
        return ''

def generate_index_html(projects):
    filter_html = '''
    <div class="filter-bar" id="filterBar">
      <button class="filter-btn" data-filter="#selected">#SELECTED</button>
      <button class="filter-btn" data-filter="#architecture">#ARCHITECTURE</button>
      <button class="filter-btn" data-filter="#tech">#TECH</button>
      <button class="filter-btn" data-filter="#art">#ART</button>
      <button class="filter-btn" data-action="toggle">#FUN</button>
    </div>
    '''
    import html as _html
    cards = []
    for proj in projects:
        icon_src = proj["icon"]
        if icon_src.startswith("../"):
            icon_src = icon_src[3:]
        if not icon_src:
            icon_src = f"projects/{proj['num']}/icon.svg"
        cards.append(f'''
        <a class="project" data-project="{proj['num']}" data-hashtags="{' '.join(proj['hashtags'])}" href="{PROJECT_HTML_DIR}/project{proj['num']}.html">
          <img src="{icon_src}" alt="icon" class="project-logo" />
          <span class="project-label">{proj['num']}</span>
          <span class="project-tooltip">{_html.escape(proj.get('titledesc','')).replace(chr(10),'<br />')}</span>
        </a>
        ''')
    grid_html = "\n".join(cards)
    return f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Ivan Bagaturiya</title>
    <link rel="stylesheet" href="assets/css/index.css" />
  </head>
  <body>
    {filter_html}
    <main class="main">
      <div class="grid" id="projectGrid">
        {grid_html}
      </div>
    </main>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/matter-js/0.19.0/matter.min.js"></script>
    <script src="assets/js/site.js"></script>
    <div class="mouse-line-vertical"></div>
    <div class="mouse-line-horizontal"></div>
    <script>
      // Mouse-following lines animation (always visible)
      const vLine = document.querySelector('.mouse-line-vertical');
      const hLine = document.querySelector('.mouse-line-horizontal');
      // Make lines more responsive by removing transition delay
      if (vLine && hLine) {{
        vLine.style.transition = 'none';
        hLine.style.transition = 'none';
      }}
      document.addEventListener('mousemove', function(e) {{
        if (vLine) vLine.style.left = e.clientX + 'px';
        if (hLine) hLine.style.top = e.clientY + 'px';
      }});
    </script>

    <div class="background-layer">
      <!-- centered background branding text -->
      <div class="background-text" id="backgroundText" role="button" tabindex="0" aria-label="Show about project">
        I.A.B</br />
        Ivan</br />
        Bagaturiya</br />
        Architect
      </div>
      <svg class="direction-arrow" id="directionArrow" viewBox="0 0 140 20" aria-hidden="true">
        <line x1="0" y1="10" x2="140" y2="10"></line>
      </svg>
    </div>

    {copyright}
  </body>
</html>
'''


def html_items(values, class_name="cv-list"):
    items = "".join(f"<li>{escape(str(value))}</li>" for value in values if value)
    return f'<ul class="{class_name}">{items}</ul>' if items else ""


def contact_href(key, value):
    if key == "email":
        return f"mailto:{value}"
    if key == "phone":
        return f"tel:{re.sub(r'[^+0-9]', '', value)}"
    if key in {"website", "linkedin", "instagram"}:
        return value if value.startswith(("http://", "https://")) else f"https://{value}"
    return ""


def contact_icon_src(key):
    if key == "email":
        return "../assets/icons/email.svg"
    if key == "phone":
        return "../assets/icons/phone.svg"
    if key == "linkedin":
        return "../assets/icons/linkedin.svg"
    if key == "instagram":
        return "../assets/icons/instagram.svg"
    return ""


def contact_icon_svg(key):
    if key == "email":
        return (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M4 5h16c1.1 0 2 .9 2 2v10c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V7c0-1.1.9-2 2-2zm0 2v.01L12 12.01 20 7.01V7H4zm0 12h16V9.24l-8 5.33-8-5.33V19z"/>'
            '</svg>'
        )
    if key == "linkedin":
        return (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M4 4h16v16H4V4zm3.5 3.75a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5zM7 18h3.5V10H7v8zm5 0h3.5v-4.5c0-1.07-.86-1.5-1.25-1.5-.39 0-1.25.43-1.25 1.5V18zm0-10.75h3.5V8H12v-.75z"/>'
            '</svg>'
        )
    if key == "instagram":
        return (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M7 2C4.24 2 2 4.24 2 7v10c0 2.76 2.24 5 5 5h10c2.76 0 5-2.24 5-5V7c0-2.76-2.24-5-5-5H7zm11 2a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3h11zm-5 3.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9zm0 2a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zm4.75-.75a1.25 1.25 0 1 1 0 2.5 1.25 1.25 0 0 1 0-2.5z"/>'
            '</svg>'
        )
    return ""


def generate_about_html(project_folder):
    with CV_DATA_PATH.open("r", encoding="utf-8") as handle:
        cv = json.load(handle)
    with ABOUT_TEMPLATE.open("r", encoding="utf-8") as handle:
        template = handle.read()

    contact_rows = []
    icon_links = []
    for key in ("location", "phone", "email", "website", "linkedin", "instagram"):
        value = cv.get("contact", {}).get(key)
        if not value:
            continue
        if key == "website":
            continue
        href = contact_href(key, value)
        if key in {"email", "phone", "linkedin", "instagram"}:
            external = ' target="_blank" rel="noopener noreferrer"' if key in {"linkedin", "instagram"} else ""
            icon_src = contact_icon_src(key)
            icon_links.append(
                f'<a class="contact-icon" href="{escape(href, quote=True)}"{external} aria-label="{escape(key)}">'
                f'<img src="{escape(icon_src, quote=True)}" alt="{escape(key)} icon" />'
                '</a>'
            )
            continue
        content = escape(str(value))
        if href:
            content = f'<a href="{escape(href, quote=True)}">{content}</a>'
        contact_rows.append(
            f'<div class="contact-row"><dt>{escape(key)}</dt><dd>{content}</dd></div>'
        )

    profile_blocks = []
    if cv.get("profile_en"):
        profile_blocks.append(
            f'<div class="profile-language"><p>{escape(cv["profile_en"])}</p></div>'
        )

    skill_groups = []
    for group in cv.get("skill_groups", []):
        skill_groups.append(
            '<article class="skill-group">'
            f'<h3>{escape(group.get("name", "Skills"))}</h3>'
            f'{html_items(group.get("items", []), "chip-list")}'
            '</article>'
        )

    experience_entries = []
    for entry in cv.get("experience", []):
        location = f' · {escape(entry["location"])}' if entry.get("location") else ""
        experience_entries.append(
            '<article class="timeline-entry">'
            '<header>'
            f'<h3>{escape(entry.get("role", ""))}</h3>'
            f'<time>{escape(entry.get("dates", ""))}</time>'
            '</header>'
            f'<p class="institution">{escape(entry.get("company", ""))}{location}</p>'
            f'{html_items(entry.get("highlights", []))}'
            '</article>'
        )

    education_entries = []
    for entry in cv.get("education", []):
        professors = entry.get("professors", [])
        professor_html = ""
        if professors:
            professor_html = (
                '<div class="professors"><span>Professors</span>'
                f'{html_items(professors, "inline-list")}</div>'
            )
        education_entries.append(
            '<article class="timeline-entry education-entry">'
            '<header>'
            f'<h3>{escape(entry.get("qualification", ""))}</h3>'
            f'<time>{escape(entry.get("dates", ""))}</time>'
            '</header>'
            f'<p class="institution">{escape(entry.get("institution", ""))}</p>'
            f'{professor_html}'
            '</article>'
        )

    hobby_groups = []
    for category in cv.get("hobbies", {}).get("categories", []):
        hobby_groups.append(
            '<article class="hobby-group">'
            f'<h3>{escape(category.get("name", "Interests"))}</h3>'
            f'{html_items(category.get("items", []))}'
            '</article>'
        )

    replacements = {
        "{{CV_NAME}}": escape(cv.get("name", "")),
        "{{CV_INITIALS}}": escape(cv.get("initials", "")),
        "{{CV_HEADLINE}}": escape(cv.get("headline", "")),
        "{{CV_HEADLINE_DE}}": escape(cv.get("headline_de", cv.get("headline", ""))),
        "{{CV_PORTRAIT}}": f"../projects/{escape(project_folder, quote=True)}/image1.png",
        "{{CV_CONTACT}}": "".join(contact_rows),
        "{{CV_CONTACT_ICONS}}": "".join(icon_links),
        "{{CV_PROFILES}}": "".join(profile_blocks),
        "{{CV_SKILLS}}": "".join(skill_groups),
        "{{CV_EXPERIENCE}}": "".join(experience_entries),
        "{{CV_EDUCATION}}": "".join(education_entries),
        "{{CV_LANGUAGES}}": html_items(cv.get("languages", []), "chip-list"),
        "{{CV_HOBBIES}}": "".join(hobby_groups),
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template

def generate_project_html(project_num, project_folder, title, desc, icon, media, next_project, prev_project, all_projects=None):
    # Read the template
    with PROJECT_TEMPLATE.open("r", encoding="utf-8") as f:
        template = f.read()

    # Find trailer (mp4, gif, or txt for embed)
    trailer = ""
    trailer_ext = ""
    trailer_html = ""
    # Check for trailer.txt (embed code)
    trailer_txt_path = safe_join(PROJECTS_DIR, project_folder, "trailer.txt")
    if os.path.exists(trailer_txt_path):
      trailer_html = read_file(trailer_txt_path)
      if trailer_html.startswith('http'):
        trailer_html = f'<a href="{trailer_html}" target="_blank" style="color:#fff;text-decoration:underline;">View Website</a>'
    else:
      for ext in [".mp4", ".gif"]:
        trailer_path = safe_join(PROJECTS_DIR, project_folder, f"trailer{ext}")
        if os.path.exists(trailer_path):
          # compute path relative to where project html files will live
          project_base = os.path.join(OUTPUT_DIR, PROJECT_HTML_DIR)
          trailer = os.path.relpath(trailer_path, project_base).replace("\\", "/")
          trailer_ext = ext
          break
      if trailer:
        if trailer_ext == ".mp4":
          trailer_html = f'<video class="project-trailer" src="{trailer}" autoplay loop muted playsinline></video>'
        elif trailer_ext == ".gif":
          trailer_html = f'<img class="project-trailer" src="{trailer}" alt="Trailer" />'

    # Media (exclude trailer) - group by numbered prefix so items with the same
    # number share a row and later numbers appear below in order.
    non_trailer_media = [item for item in media if not item["src"].endswith("trailer.mp4") and not item["src"].endswith("trailer.gif")]
    grouped_media = []
    for item in non_trailer_media:
        if not grouped_media or grouped_media[-1][-1]["number"] != item["number"]:
            grouped_media.append([item])
        else:
            grouped_media[-1].append(item)

    rows_html = []
    for group in grouped_media:
        items_html = "".join(media_html_tag(item["src"]) for item in group)
        row_class = "project-media-row" if len(group) == 1 else "project-media-row project-media-row--multi"
        rows_html.append(f'<div class="{row_class}">{items_html}</div>')
    images_html = "\n".join(rows_html)

    # Navigation SVGs (same for all, just direction changes)
    svg_left = '<svg viewBox="0 0 60 60" width="80" height="80" style="overflow:visible;" xmlns="http://www.w3.org/2000/svg"><polyline points="40,10 20,30 40,50" fill="none" stroke="#bbb" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    svg_up = '<svg viewBox="0 0 60 60" width="80" height="80" style="overflow:visible;" xmlns="http://www.w3.org/2000/svg"><polyline points="10,40 30,20 50,40" fill="none" stroke="#bbb" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    svg_right = '<svg viewBox="0 0 60 60" width="80" height="80" style="overflow:visible;" xmlns="http://www.w3.org/2000/svg"><polyline points="20,10 40,30 20,50" fill="none" stroke="#bbb" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    nav_html = '<div class="project-nav" style="gap:0;">'
    if prev_project:
        nav_html += f'<a class="nav-btn" href="project{prev_project}.html" title="Previous" style="background:none;box-shadow:none;">{svg_left}</a>'
    else:
      nav_html += f'<span class="nav-btn disabled" style="background:none;box-shadow:none;">{svg_left}</span>'
    # when project pages live in a subfolder, link back to root index
    nav_html += f'<a class="nav-btn" href="../index.html" title="Back to index" style="background:none;box-shadow:none;">{svg_up}</a>'
    if next_project:
        nav_html += f'<a class="nav-btn" href="project{next_project}.html" title="Next" style="background:none;box-shadow:none;">{svg_right}</a>'
    else:
        nav_html += f'<span class="nav-btn disabled" style="background:none;box-shadow:none;">{svg_right}</span>'
    nav_html += '</div>'

    # Generate "You might also like" section
    also_like_html = ""
    if all_projects:
        # Get current project hashtags
        current_hashtags = set(get_hashtags(safe_join(PROJECTS_DIR, project_folder)))
        # Find projects with shared hashtags
        related_projects = [p for p in all_projects if p['num'] != project_num and set(p['hashtags']) & current_hashtags]
        if related_projects:
            random_project = sorted(
                related_projects, key=lambda project: project["num"], reverse=True
            )[0]
            icon_src = random_project['icon'] if random_project['icon'] else f"../projects/{random_project['folder']}/icon.svg"
            also_like_html = f'''<div class="also-like-section">
      <p class="also-like-title">u might also like</p>
      <div class="also-like-container">
        <a class="also-like-project" href="project{random_project['num']}.html">
          <img src="{icon_src}" alt="icon" class="also-like-img" />
          <span class="also-like-label">{random_project['num']}</span>
        </a>
      </div>
    </div>
    '''

    # Replace placeholders in template
    html = template
    if project_num == "2409":
        html = html.replace("../assets/css/project.css", "../assets/css/about.css")
    html = html.replace("{{PROJECT_NUM}}", project_num)
    html = html.replace("{{TITLE}}", title)
    html = html.replace("{{DESC}}", desc.replace('\n', '<br />'))
    html = html.replace("{{TRAILER}}", trailer_html)
    html = html.replace("{{IMAGES}}", images_html)
    html = html.replace("{{NAV}}", nav_html)
    html = html.replace("{{ALSO_LIKE}}", also_like_html)
    return html

def main():
    folder_by_id = discover_project_folders()
    project_ids = sorted(folder_by_id, key=int, reverse=True)

    # First pass: collect all project metadata
    projects = []
    for idx, project_id in enumerate(project_ids):
        folder = folder_by_id[project_id]
        folder_path = safe_join(PROJECTS_DIR, folder)
        title = read_file(safe_join(folder_path, "title.txt"))
        desc = read_file(safe_join(folder_path, "description.txt"))
        # new file containing short description used on index hover tooltip
        titledesc = read_file(safe_join(folder_path, "titledescription.txt"))
        icon = get_icon(folder_path)
        media = get_media(folder_path)
        hashtags = get_hashtags(folder_path)
        next_project = project_ids[idx + 1] if idx + 1 < len(project_ids) else ""
        prev_project = project_ids[idx - 1] if idx - 1 >= 0 else ""
        projects.append({
            "num": project_id,
            "folder": folder,
            "title": title,
            "desc": desc,
            "titledesc": titledesc,
            "icon": icon,
            "media": media,
            "hashtags": hashtags,
            "next": next_project
        })

    # Second pass: generate HTML files with complete projects list
    for idx, project_id in enumerate(project_ids):
        if project_id == "2409":
            out_dir = os.path.join(OUTPUT_DIR, PROJECT_HTML_DIR)
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, "project2409.html"), "w", encoding="utf-8") as f:
                f.write(generate_about_html(folder_by_id[project_id]))
            continue
        folder = folder_by_id[project_id]
        folder_path = safe_join(PROJECTS_DIR, folder)
        title = read_file(safe_join(folder_path, "title.txt"))
        desc = read_file(safe_join(folder_path, "description.txt"))
        icon = get_icon(folder_path)
        media = get_media(folder_path)
        next_project = project_ids[idx + 1] if idx + 1 < len(project_ids) else ""
        prev_project = project_ids[idx - 1] if idx - 1 >= 0 else ""
        html = generate_project_html(project_id, folder, title, desc, icon, media, next_project, prev_project, projects)
        # ensure output directory exists
        out_dir = os.path.join(OUTPUT_DIR, PROJECT_HTML_DIR)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"project{project_id}.html"), "w", encoding="utf-8") as f:
          f.write(html)

    index_html = generate_index_html(projects)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("Site generated!")

if __name__ == "__main__":
    main()
