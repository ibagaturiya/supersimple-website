import os
import re

PROJECTS_DIR = "projects"
OUTPUT_DIR = "."
CSS_FILE = "styles.css"

def is_safe_folder(name):
    return re.fullmatch(r'\d{4,}', name) is not None

def safe_join(base, *paths):
    final_path = os.path.abspath(os.path.join(base, *paths))
    if not final_path.startswith(os.path.abspath(base)):
        raise ValueError("Unsafe path detected!")
    return final_path

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ""

def get_icon(folder):
    """
    Return the relative path to icon.svg if it exists, else ''.
    """
    icon_path = safe_join(folder, "icon.svg")
    if os.path.exists(icon_path):
        return os.path.relpath(icon_path, OUTPUT_DIR).replace("\\", "/")
    return ""

def get_media(folder):
    """
    Return a list of up to 5 media files (image/video/audio) in the given folder.
    Supported: .jpg, .jpeg, .gif, .mp4, .mp3, .png, .pdf
    """
    media = []
    exts = [".jpg", ".jpeg", ".gif", ".mp4", ".mp3", ".png", ".pdf"]
    for i in range(1, 6):
        for ext in exts:
            fname = f"image{i}{ext}"
            media_path = safe_join(folder, fname)
            if os.path.exists(media_path):
                rel_path = os.path.relpath(media_path, OUTPUT_DIR).replace("\\", "/")
                media.append(rel_path)
                break  # Only one file per slot
    return media

def get_hashtags(folder):
    hashtags_path = safe_join(folder, "hashtags.txt")
    hashtags = read_file(hashtags_path)
    tags = re.findall(r'#\w+', hashtags)
    return [tag.lower() for tag in tags]

def media_html_tag(src):
    """
    Return the correct HTML tag for the given media file.
    """
    if src.lower().endswith(('.jpg', '.jpeg', '.gif', '.png', '.svg')):
        return f'<img src="{src}" alt="" />'
    elif src.lower().endswith('.mp4'):
        return f'<video src="{src}" controls loop muted playsinline style="width:100%;border-radius:10px;background:#000;min-height:120px;max-height:340px;"></video>'
    elif src.lower().endswith('.mp3'):
        return f'<audio src="{src}" controls style="width:100%;margin-top:8px;"></audio>'
    elif src.lower().endswith('.pdf'):
        return f'<a href="{src}" target="_blank" style="display:block;margin:10px 0;color:#111;font-weight:bold;">View PDF</a>'
    else:
        return ''

def generate_index_html(projects):
    toggle_html = """
  <div class="center-toggle">
    <label class="switch">
      <input type="checkbox" id="bubbleToggle" />
      <span class="slider"></span>
    </label>
  </div>
"""
    filter_html = """
  <div class="filter-bar" id="filterBar">
    <button class="filter-btn" data-filter="#selected">#SELECTED</button>
    <div class="filter-group">
      <button class="filter-btn" data-filter="#architecture">#ARCHITECTURE</button>
      <div class="subfilters">
        <button class="filter-btn subfilter" data-filter="#eth">#ETH</button>
        <button class="filter-btn subfilter" data-filter="#nh">#NH</button>
      </div>
    </div>
    <button class="filter-btn" data-filter="#art">#ART</button>
    <button class="filter-btn" data-filter="#music">#MUSIC</button>
    <button class="filter-btn" data-filter="#tech">#TECH</button>
    <button class="filter-btn" data-filter="#photo">#PHOTO</button>
  </div>
"""
    grid_html = "\n".join(
        f"""
        <a class="project" data-hashtags="{' '.join(proj['hashtags'])}" href="project{proj['num']}.html">
          {'<img src="' + proj['icon'] + '" alt="icon" class="project-logo" />' if proj['icon'] else ''}
          <span class="project-label">{proj['num']}</span>
        </a>
        """ for proj in projects
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Portfolio Grid</title>
  <link rel="stylesheet" href="{CSS_FILE}" />
</head>
{toggle_html}
<body>
  {filter_html}
  <main class="main">
    <div class="grid" id="projectGrid">
      {grid_html}
    </div>
  </main>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/matter-js/0.19.0/matter.min.js"></script>
  <script src="script.js"></script>
</body>
</html>
"""

def main():
    all_folders = [
        f for f in os.listdir(PROJECTS_DIR)
        if os.path.isdir(safe_join(PROJECTS_DIR, f)) and is_safe_folder(f)
    ]
    project_folders = sorted(all_folders)[::-1]

    projects = []
    for idx, folder in enumerate(project_folders):
        folder_path = safe_join(PROJECTS_DIR, folder)
        title = read_file(safe_join(folder_path, "title.txt"))
        desc = read_file(safe_join(folder_path, "description.txt"))
        icon = get_icon(folder_path)
        media = get_media(folder_path)
        hashtags = get_hashtags(folder_path)
        next_project = project_folders[idx + 1] if idx + 1 < len(project_folders) else ""
        projects.append({
            "num": folder,
            "title": title,
            "desc": desc,
            "icon": icon,
            "media": media,
            "hashtags": hashtags,
            "next": next_project
        })
        html = generate_project_html(folder, title, desc, icon, media, next_project)
        with open(os.path.join(OUTPUT_DIR, f"project{folder}.html"), "w", encoding="utf-8") as f:
            f.write(html)

    index_html = generate_index_html(projects)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("Site generated!")

def generate_project_html(project_num, title, desc, icon, media, next_project):
    media_html = "\n".join(
        media_html_tag(src) for src in media
    )
    next_btn = (
        f'<a class="next-btn" href="project{next_project}.html">Next project →</a>'
        if next_project else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{project_num} – {title}</title>
  <link rel="stylesheet" href="{CSS_FILE}" />
  <!-- ...styles omitted for brevity... -->
</head>
<body>
  <div class="project-page">
    <div class="project-number">{project_num}</div>
    <div class="project-title">{title}</div>
    <div class="project-text">{desc}</div>
    <div class="project-images">{media_html}</div>
    {next_btn}
  </div>
</body>
</html>
"""

if __name__ == "__main__":
    main()