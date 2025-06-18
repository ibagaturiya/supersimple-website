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
    icon_path = safe_join(folder, "icon.svg")
    if os.path.exists(icon_path):
        return os.path.relpath(icon_path, OUTPUT_DIR).replace("\\", "/")
    return ""

def get_media(folder):
    media = []
    exts = [".jpg", ".jpeg", ".gif", ".mp4", ".mp3", ".png", ".pdf"]
    for i in range(1, 6):
        for ext in exts:
            fname = f"image{i}{ext}"
            media_path = safe_join(folder, fname)
            if os.path.exists(media_path):
                rel_path = os.path.relpath(media_path, OUTPUT_DIR).replace("\\", "/")
                media.append(rel_path)
                break
    return media

def get_hashtags(folder):
    hashtags_path = safe_join(folder, "hashtags.txt")
    hashtags = read_file(hashtags_path)
    tags = re.findall(r'#\w+', hashtags)
    return [tag.lower() for tag in tags]

def media_html_tag(src):
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
      <input type="range" id="styleToggle" min="0" max="2" value="0" />
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
    <button class="filter-btn" data-filter="#tech">#TECH</button>
    <button class="filter-btn" data-filter="#photo">#PHOTO</button>
    <button class="filter-btn" data-filter="#music">#MUSIC</button>
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
  <link id="theme-css" rel="stylesheet" href="{CSS_FILE}" />
</head>
<body>
  {toggle_html}
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

def generate_project_html(project_num, title, desc, icon, media, next_project, prev_project):
    # Find trailer (mp4 or gif)
    trailer = ""
    for ext in [".mp4", ".gif"]:
        trailer_path = os.path.join(PROJECTS_DIR, project_num, f"trailer{ext}")
        if os.path.exists(trailer_path):
            trailer = os.path.relpath(trailer_path, OUTPUT_DIR).replace("\\", "/")
            break

    # Images (exclude trailer)
    image_media = [src for src in media if not src.endswith("trailer.mp4") and not src.endswith("trailer.gif")]

    # Navigation buttons
    nav_html = f"""
    <div class="project-nav">
      {'<a class="nav-btn" href="project' + prev_project + '.html" title="Previous">&#8592;</a>' if prev_project else '<span class="nav-btn disabled">&#8592;</span>'}
      <a class="nav-btn" href="index.html" title="Back to index">&#8593;</a>
      {'<a class="nav-btn" href="project' + next_project + '.html" title="Next">&#8594;</a>' if next_project else '<span class="nav-btn disabled">&#8594;</span>'}
    </div>
    """

    # Trailer HTML
    trailer_html = ""
    if trailer.endswith(".mp4"):
        trailer_html = f"""
        <video class="project-trailer" src="{trailer}" autoplay loop muted playsinline></video>
        """
    elif trailer.endswith(".gif"):
        trailer_html = f"""
        <img class="project-trailer" src="{trailer}" alt="trailer" />
        """

    # Images column
    images_html = "\n".join(
        media_html_tag(src) for src in image_media
    )

    # Title row (overlayed)
    title_html = f"""
    <div class="project-header-overlay">
      <span class="project-title">{title}</span>
    </div>
    """

    # Description (left column)
    desc_html = f"""
    <div class="project-desc">
      {desc.replace('\n', '<br />')}
    </div>
    """

    # Main content split
    main_html = f"""
    <div class="project-main">
      <div class="project-left">
        {desc_html}
      </div>
      <div class="project-right">
        {images_html}
      </div>
    </div>
    """

    # Fixed project number (top left)
    number_fixed_html = f"""
    <a href="index.html" class="project-number-fixed">{project_num}</a>
    """

    # Full HTML
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{project_num} – {title}</title>
  <link rel="stylesheet" href="{CSS_FILE}" />
  <style>
    body {{
      margin: 0; background: #fff; color: #111; font-family: Arial,sans-serif;
    }}
    .project-hero {{
      position: relative;
      width: 100vw;
      max-height: 340px;
      overflow: hidden;
    }}
    .project-trailer {{
      display: block;
      width: 100vw;
      max-height: 340px;
      object-fit: cover;
      margin: 0 auto;
      background: #000;
      cursor: pointer;
      z-index: 1;
      position: relative;
    }}
    .project-header-overlay {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100vw;
      z-index: 2;
      text-align: center;
      padding: 32px 0 0 0;
      background: linear-gradient(180deg,rgba(0,0,0,0.55) 0,rgba(0,0,0,0.05) 100%);
    }}
    .project-title {{
      text-decoration: none;
      color: #fff;
      font-size: 2.2rem;
      font-weight: bold;
      display: inline-block;
      letter-spacing: 0.01em;
      cursor: pointer;
      padding: 0 16px;
    }}
    .project-number-fixed {{
      position: fixed;
      top: 18px;
      left: 18px;
      z-index: 100;
      background: rgba(0,0,0,0.72);
      color: #fff;
      font-size: 1.1rem;
      font-weight: bold;
      border-radius: 8px;
      padding: 6px 14px;
      text-decoration: none;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      transition: background 0.18s;
      opacity: 0.92;
    }}
    .project-number-fixed:hover {{
      background: #111;
      color: #fff;
      opacity: 1;
    }}
    .project-main {{
      display: flex;
      flex-direction: row;
      gap: 32px;
      max-width: 1200px;
      margin: 0 auto;
      padding: 48px 24px 24px 24px;
      position: relative;
      z-index: 2;
    }}
    .project-left {{
      flex: 1 1 40%;
      max-width: 40%;
      font-size: 1.15rem;
      line-height: 1.7;
      padding-right: 24px;
      word-break: break-word;
    }}
    .project-right {{
      flex: 1 1 60%;
      max-width: 60%;
      display: flex;
      flex-direction: column;
      gap: 18px;
      align-items: flex-start;
    }}
    .project-right img, .project-right video, .project-right audio {{
      width: 100%;
      max-width: 100%;
      border-radius: 12px;
      background: #eee;
    }}
    hr {{
      border: none;
      border-top: 2px solid #eee;
      margin: 0 0 0 0;
      height: 0;
      width: 100%;
      position: relative;
      z-index: 2;
    }}
    .project-nav {{
      display: flex;
      justify-content: center;
      gap: 32px;
      margin: 48px 0 24px 0;
      z-index: 2;
      position: relative;
    }}
    .nav-btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: #111;
      color: #fff;
      font-size: 2rem;
      border: none;
      text-decoration: none;
      cursor: pointer;
      transition: background 0.18s;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      user-select: none;
    }}
    .nav-btn:hover:not(.disabled) {{
      background: #333;
    }}
    .nav-btn.disabled {{
      background: #bbb;
      color: #fff;
      cursor: default;
      pointer-events: none;
    }}
    @media (max-width: 900px) {{
      .project-main {{
        flex-direction: column;
        gap: 18px;
        padding: 32px 4vw 16px 4vw;
      }}
      .project-left, .project-right {{
        max-width: 100%;
        padding: 0;
      }}
    }}
    @media (max-width: 600px) {{
      .project-header-overlay {{
        padding-top: 16px;
      }}
      .project-main {{
        padding: 16px 2vw 8px 2vw;
      }}
      .nav-btn {{
        width: 38px; height: 38px; font-size: 1.3rem;
      }}
    }}
  </style>
</head>
<body>
  {number_fixed_html}
  <div class="project-hero">
    {trailer_html}
    {title_html}
  </div>
  <hr />
  {main_html}
  {nav_html}
<script>
  const trailer = document.querySelector('.project-trailer');
  if(trailer && trailer.tagName === "VIDEO") {{
    trailer.muted = true;
    trailer.autoplay = true;
    trailer.playsInline = true;
    trailer.play().catch(function() {{
      // Try to play again on user interaction if autoplay was blocked
      const tryPlay = function() {{
        trailer.play();
        window.removeEventListener('click', tryPlay);
      }};
      window.addEventListener('click', tryPlay);
    }});
  }}
  if(trailer) {{
    trailer.addEventListener('click', function() {{
      if (trailer.requestFullscreen) trailer.requestFullscreen();
      else if (trailer.webkitRequestFullscreen) trailer.webkitRequestFullscreen();
      else if (trailer.msRequestFullscreen) trailer.msRequestFullscreen();
    }});
  }}
</script>
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
        prev_project = project_folders[idx - 1] if idx - 1 >= 0 else ""
        projects.append({
            "num": folder,
            "title": title,
            "desc": desc,
            "icon": icon,
            "media": media,
            "hashtags": hashtags,
            "next": next_project
        })
        html = generate_project_html(folder, title, desc, icon, media, next_project, prev_project)
        with open(os.path.join(OUTPUT_DIR, f"project{folder}.html"), "w", encoding="utf-8") as f:
            f.write(html)

    index_html = generate_index_html(projects)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("Site generated!")

if __name__ == "__main__":
    main()