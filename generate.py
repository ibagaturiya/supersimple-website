import os

# --- CONFIGURATION ---

PROJECTS_DIR = "projects"  # Folder where all project folders live
OUTPUT_DIR = "."           # Where to write the generated HTML files
CSS_FILE = "styles.css"    # Your CSS file for all pages

# --- HELPER FUNCTIONS ---

def read_file(path):
    """Read and return the contents of a text file, or an empty string if not found."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ""

def get_images(folder):
    """Return a list of up to 5 image paths (image1.jpg to image5.jpg) in the given folder."""
    images = []
    for i in range(1, 6):
        img_path = os.path.join(folder, f"image{i}.jpg")
        if os.path.exists(img_path):
            images.append(img_path.replace("\\", "/"))  # For Windows compatibility
    return images

# --- HTML GENERATION FUNCTIONS ---

def generate_project_html(project_num, title, desc, images, next_project):
    """
    Generate the HTML for a single project page.
    - project_num: e.g. "0001"
    - title: project title
    - desc: project description
    - images: list of image paths
    - next_project: number of the next project, or "" if last
    """
    # Generate the HTML for the images
    images_html = "\n".join(
        f'<img src="{img}" alt="{title}" />' for img in images
    )
    # Generate the "Next project" button if there is a next project
    next_btn = (
        f'<a class="next-btn" href="project{next_project}.html">Next project →</a>'
        if next_project else ""
    )
    # Return the complete HTML page as a string
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
    Generate the main grid HTML (index.html) with a tile for each project.
    - projects: list of dictionaries with project info
    """
    grid_items = []
    for i, proj in enumerate(projects):
        img = proj['images'][0] if proj['images'] else ""
        grid_items.append(f"""
        <a class="project" data-tags="" href="project{proj['num']}.html">
          <img src="{img}" alt="{proj['num']}" class="project-img" />
          <span class="project-label">{proj['num']}</span>
        </a>
        """)
    grid_html = "\n".join(grid_items)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Portfolio Grid</title>
  <link rel="stylesheet" href="{CSS_FILE}" />
</head>
<body>
  <main class="main">
    <div class="grid" id="projectGrid">
      {grid_html}
    </div>
  </main>
</body>
</html>
"""

# --- MAIN SCRIPT ---

def main():
    # Get a sorted list of all project folders (e.g. ['0001', '0002', ...])
    project_folders = sorted([f for f in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, f))])
    
    projects = []
    # Loop through each project folder
    for idx, folder in enumerate(project_folders):
        folder_path = os.path.join(PROJECTS_DIR, folder)
        title = read_file(os.path.join(folder_path, "title.txt"))         # Read title
        desc = read_file(os.path.join(folder_path, "description.txt"))   # Read description
        images = get_images(folder_path)                                 # Get up to 5 images
        next_project = project_folders[idx + 1] if idx + 1 < len(project_folders) else ""  # Next project number, or "" if last
        
        # Store info for generating index.html
        projects.append({
            "num": folder,
            "title": title,
            "desc": desc,
            "images": images,
            "next": next_project
        })
        
        # Generate the HTML for this project page and save it
        html = generate_project_html(folder, title, desc, images, next_project)
        with open(os.path.join(OUTPUT_DIR, f"project{folder}.html"), "w", encoding="utf-8") as f:
            f.write(html)
    
    # Generate the main grid (index.html)
    index_html = generate_index_html(projects)
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("Site generated!")

if __name__ == "__main__":
    main()
