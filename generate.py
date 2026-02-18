import os
import re

PROJECTS_DIR = "projects"
OUTPUT_DIR = "."
PROJECT_HTML_DIR = "projecthtml"
CSS_FILE = "styles.css"


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
  Ivan Bagaturiya &mdash;
  <script>
    document.write(document.lastModified);
  </script>
</span>
'''

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
    for ext in [".svg", ".png", ".jpg", ".jpeg", ".gif"]:
        icon_path = safe_join(folder, f"icon{ext}")
        if os.path.exists(icon_path):
            # compute path relative to where project html files will live
            project_base = os.path.join(OUTPUT_DIR, PROJECT_HTML_DIR)
            return os.path.relpath(icon_path, project_base).replace("\\", "/")
    return ""

def get_media(folder):
    media = []
    exts = [".jpg", ".jpeg", ".gif", ".mp4", ".mp3", ".png", ".pdf"]
    # Support both 'image1' and 'image 1' (with space)
    for i in range(1, 10):
        for ext in exts:
            for prefix in [f"image{i}", f"image {i}"]:
                fname = f"{prefix}{ext}"
                media_path = safe_join(folder, fname)
                if os.path.exists(media_path):
                    project_base = os.path.join(OUTPUT_DIR, PROJECT_HTML_DIR)
                    rel_path = os.path.relpath(media_path, project_base).replace("\\", "/")
                    media.append(rel_path)
                    break
            else:
                continue
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
    toggle_html = '''
    <div class="center-toggle">
      <div class="switch">
        <label for="bubbleToggle">
          <input id="bubbleToggle" type="checkbox" />
          <div class="sun-moon">
            <div class="dots"></div>
          </div>
          <div class="background">
            <div class="stars1"></div>
            <div class="stars2"></div>
          </div>
          <div class="fill"></div>
        </label>
      </div>
    </div>
    '''
    filter_html = '''
    <div class="filter-bar" id="filterBar">
      <button class="filter-btn" data-filter="#selected">#SELECTED</button>
      <button class="filter-btn" data-filter="#architecture">#ARCHITECTURE</button>
      <button class="filter-btn" data-filter="#tech">#TECH</button>
      <button class="filter-btn" data-filter="#art">#ART</button>
      <button class="filter-btn" data-filter="#music">#MUSIC</button>
    </div>
    '''
    grid_html = "\n".join(
        f'''
        <a class="project" data-project="{proj['num']}" data-hashtags="{' '.join(proj['hashtags'])}" href="{PROJECT_HTML_DIR}/project{proj['num']}.html">
          <img src="projects/{proj['num']}/icon.svg" alt="icon" class="project-logo" />
          <span class="project-label">{proj['num']}</span>
        </a>
        ''' for proj in projects
    )
    dynamic_icon_js = '''
    <script>
      // Dynamically set icon file extension for each project
      (function () {
        const exts = ["svg", "png", "jpg", "jpeg", "gif", "pdf"];
        document.querySelectorAll(".project").forEach((project) => {
          const projectNum = project.getAttribute("data-project");
          const img = project.querySelector("img.project-logo");
          if (!projectNum || !img) return;
          (function tryNext(i) {
            if (i >= exts.length) return;
            const url = `projects/${projectNum}/icon.${exts[i]}`;
            fetch(url, { method: "HEAD" })
              .then((r) => {
                if (r.ok) img.src = url;
                else tryNext(i + 1);
              })
              .catch(() => tryNext(i + 1));
          })(0);
        });
      })();
    </script>
    '''
    return f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Ivan Bagaturiya</title>
    <link rel="stylesheet" href="styles.css" />
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
    {dynamic_icon_js}
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
    {copyright}
  </body>
</html>
'''

def generate_project_html(project_num, title, desc, icon, media, next_project, prev_project, all_projects=None):
    # Read the template
    with open("projectTEMPLATE.html", "r", encoding="utf-8") as f:
        template = f.read()

    # Find trailer (mp4, gif, or txt for embed)
    trailer = ""
    trailer_ext = ""
    trailer_html = ""
    # Check for trailer.txt (embed code)
    trailer_txt_path = os.path.join(PROJECTS_DIR, project_num, "trailer.txt")
    if os.path.exists(trailer_txt_path):
      trailer_html = read_file(trailer_txt_path)
    else:
      for ext in [".mp4", ".gif"]:
        trailer_path = os.path.join(PROJECTS_DIR, project_num, f"trailer{ext}")
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

    # Images (exclude trailer)
    image_media = [src for src in media if not src.endswith("trailer.mp4") and not src.endswith("trailer.gif")]
    images_html = "\n".join(f'<img src="{src}" alt="" />' for src in image_media)

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
        import random
        # Get current project hashtags
        current_hashtags = set(get_hashtags(safe_join(PROJECTS_DIR, project_num)))
        # Find projects with shared hashtags
        related_projects = [p for p in all_projects if p['num'] != project_num and set(p['hashtags']) & current_hashtags]
        if related_projects:
            random_project = random.choice(related_projects)
            icon_src = random_project['icon'] if random_project['icon'] else f"projects/{random_project['num']}/icon.svg"
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
    html = html.replace("{{PROJECT_NUM}}", project_num)
    html = html.replace("{{TITLE}}", title)
    html = html.replace("{{DESC}}", desc.replace('\n', '<br />'))
    html = html.replace("{{TRAILER}}", trailer_html)
    html = html.replace("{{IMAGES}}", images_html)
    html = html.replace("{{NAV}}", nav_html)
    html = html.replace("{{ALSO_LIKE}}", also_like_html)
    return html

def main():
    all_folders = [
        f for f in os.listdir(PROJECTS_DIR)
        if os.path.isdir(safe_join(PROJECTS_DIR, f)) and is_safe_folder(f)
    ]
    project_folders = sorted(all_folders)[::-1]

    # First pass: collect all project metadata
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

    # Second pass: generate HTML files with complete projects list
    for idx, folder in enumerate(project_folders):
        folder_path = safe_join(PROJECTS_DIR, folder)
        title = read_file(safe_join(folder_path, "title.txt"))
        desc = read_file(safe_join(folder_path, "description.txt"))
        icon = get_icon(folder_path)
        media = get_media(folder_path)
        next_project = project_folders[idx + 1] if idx + 1 < len(project_folders) else ""
        prev_project = project_folders[idx - 1] if idx - 1 >= 0 else ""
        html = generate_project_html(folder, title, desc, icon, media, next_project, prev_project, projects)
        # ensure output directory exists
        out_dir = os.path.join(OUTPUT_DIR, PROJECT_HTML_DIR)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"project{folder}.html"), "w", encoding="utf-8") as f:
          f.write(html)

    index_html = generate_index_html(projects)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("Site generated!")

if __name__ == "__main__":
    main()