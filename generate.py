import os
import re

# --- CONFIGURATION ---
PROJECTS_DIR = "projects"      # Folder where all project folders live
OUTPUT_DIR = "."               # Where to write the generated HTML files
CSS_FILE = "styles.css"        # CSS file for all pages

# --- SECURITY HELPERS ---

def is_safe_folder(name):
    """
    Allow only folder names that are 4+ digits (e.g., '0001', '0023').
    Disallow any path traversal or slashes.
    """
    return re.fullmatch(r'\d{4,}', name) is not None

def safe_join(base, *paths):
    """
    Join paths and ensure the result is inside the base directory.
    """
    final_path = os.path.abspath(os.path.join(base, *paths))
    if not final_path.startswith(os.path.abspath(base)):
        raise ValueError("Unsafe path detected!")
    return final_path

# --- HELPER FUNCTIONS ---

def read_file(path):
    """
    Read and return the contents of a text file, or an empty string if not found.
    Used for reading title.txt and description.txt in each project folder.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ""

def get_images(folder):
    """
    Return a list of up to 5 image paths (image1.jpg to image5.jpg) in the given folder.
    Used for displaying images in project pages and the grid.
    """
    images = []
    for i in range(1, 6):
        img_path = safe_join(folder, f"image{i}.jpg")
        if os.path.exists(img_path):
            # Use relative path for HTML
            rel_path = os.path.relpath(img_path, OUTPUT_DIR).replace("\\", "/")
            images.append(rel_path)
    return images

# --- HTML GENERATION FUNCTIONS ---

def generate_project_html(project_num, title, desc, images, next_project):
    """
    Generate the HTML for a single project page.
    """
    images_html = "\n".join(
        f'<img src="{img}" alt="{title}" />' for img in images
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
  <style>
    .project-page {{
      max-width: 520px;
      margin: 60px auto 0 auto;
      padding: 24px 12px 80px 12px;
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.05);
      display: flex;
      flex-direction: column;
      align-items: stretch;
      gap: 22px;
    }}
    .project-title {{
      font-size: 2.1rem;
      font-weight: 700;
      letter-spacing: 0.01em;
      margin-bottom: 6px;
    }}
    .project-number {{
      font-size: 1.1rem;
      color: #888;
      font-weight: 600;
      letter-spacing: 0.1em;
      margin-bottom: 14px;
    }}
    .project-text {{
      font-size: 1.1rem;
      line-height: 1.6;
      color: #333;
      margin-bottom: 8px;
    }}
    .project-images {{
      display: flex;
      flex-direction: column;
      gap: 16px;
      margin-bottom: 10px;
    }}
    .project-images img {{
      width: 100%;
      border-radius: 10px;
      box-shadow: 0 1px 6px rgba(0,0,0,0.06);
      object-fit: cover;
      background: #eee;
      min-height: 120px;
      max-height: 340px;
    }}
    .next-btn {{
      margin-top: 16px;
      align-self: flex-end;
      background: #111;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-family: inherit;
      font-weight: 700;
      font-size: 1.08rem;
      padding: 10px 28px;
      cursor: pointer;
      transition: background 0.18s;
      letter-spacing: 0.05em;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
      text-decoration: none;
      display: inline-block;
    }}
    .next-btn:hover, .next-btn:focus {{
      background: #333;
    }}
    @media (max-width: 600px) {{
      .project-page {{
        max-width: 100vw;
        margin: 16px 0 0 0;
        border-radius: 0;
        padding: 14px 2vw 60px 2vw;
      }}
      .project-title {{
        font-size: 1.3rem;
      }}
      .project-images img {{
        min-height: 60px;
        max-height: 200px;
      }}
    }}
  </style>
</head>
<body>
  <div class="project-page">
    <div class="project-number">{project_num}</div>
    <div class="project-title">{title}</div>
    <div class="project-text">{desc}</div>
    <div class="project-images">{images_html}</div>
    {next_btn}
  </div>
</body>
</html>
"""

def generate_index_html(projects):
    """
    Generate the HTML for the main index grid page.
    """
    toggle_html = """
  <div class="center-toggle">
    <label class="switch">
      <input type="checkbox" id="bubbleToggle" />
      <span class="slider"></span>
    </label>
  </div>
"""
    grid_html = "\n".join(
        f"""
        <a class="project" data-tags="" href="project{proj['num']}.html">
          <img src="{proj['images'][0] if proj['images'] else ''}" alt="{proj['num']}" class="project-img" />
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

# --- MAIN SCRIPT ---

def main():
    """
    Main script to generate all project pages and the index grid.
    - Reads all project folders (highest number first)
    - Generates project pages and index.html
    - Validates folder names to prevent path injection
    """
    # Get all project folders, sorted highest number first, and validate names
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
        images = get_images(folder_path)
        next_project = project_folders[idx + 1] if idx + 1 < len(project_folders) else ""
        projects.append({
            "num": folder,
            "title": title,
            "desc": desc,
            "images": images,
            "next": next_project
        })
        html = generate_project_html(folder, title, desc, images, next_project)
        with open(os.path.join(OUTPUT_DIR, f"project{folder}.html"), "w", encoding="utf-8") as f:
            f.write(html)

    index_html = generate_index_html(projects)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("Site generated!")

if __name__ == "__main__":
    main()