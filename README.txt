================================================================================
                    SUPERSIMPLE-WEBSITE WORKFLOW GUIDE
================================================================================

PROJECT OVERVIEW:
This is a portfolio website that automatically generates HTML pages from project
metadata stored in the projects/ folder. Instead of manually editing HTML, you
organize project files in folders and run generate.py to create the site.

================================================================================
FOLDER STRUCTURE:
================================================================================

/projects/
  ├── 0055/
  │   ├── title.txt          (Project title)
  │   ├── description.txt    (Project description - can use line breaks)
  │   ├── hashtags.txt       (Tags like #architecture #tech #art)
  │   ├── icon.svg/.png      (Icon shown on grid - required)
  │   ├── trailer.mp4/.gif   (Auto-plays on project page - optional)
  │   ├── trailer.txt        (Embed code alternative - optional)
  │   ├── image1.jpg         (First image on project page - optional)
  │   ├── image2.jpg         (Second image - optional)
  │   └── ... (up to image9 supported)
  │
  ├── 0054/
  ├── 0052/
  └── ... (all project folders)

NAMING RULES:
  • Folders MUST be named with 4+ digits (0055, 0054, etc.)
  • Projects are listed newest first (sorted by folder number descending)
  • Media files support: .jpg, .jpeg, .png, .gif, .svg, .mp4, .mp3, .pdf

================================================================================
STEP-BY-STEP: ADDING A NEW PROJECT BEFORE PUSHING TO GITHUB
================================================================================

1. CREATE PROJECT FOLDER
   • Create new folder in projects/ with 4-digit name (e.g., projects/0056)
   • Name should be higher than the latest project number

2. CREATE REQUIRED FILES
   Create these plain text files in your project folder:

   a) title.txt
      Content: One-line project title
      Example: "Ethereal Architecture Study"

   b) description.txt
      Content: Full project description (can have multiple lines)
      Line breaks are converted to <br /> tags
      Example:
        This is an exploration of spatial relationships
        and how light defines form in modern buildings.

   c) hashtags.txt
      Content: Space or comma-separated hashtags
      Example: #architecture #tech #art #selected
      Note: Use #selected to show on "Selected" filter

3. ADD MEDIA FILES (REQUIRED: icon, OPTIONAL: trailer/images)

   ICON (REQUIRED - shown on grid):
   • Name: icon.svg, icon.png, icon.jpg (any of these)
   • Size: Square recommended (120x120px shown on grid)
   • Format: SVG preferred for crispness

   TRAILER (OPTIONAL - auto-plays on project page):
   Option A: Video/GIF file
     • Name: trailer.mp4 or trailer.gif
     • Format: MP4 or GIF animation
   Option B: Embed code
     • Name: trailer.txt
     • Content: HTML/embed code (YouTube embed, etc.)
     • Leave trailer.mp4/.gif unused if using trailer.txt

   IMAGES (OPTIONAL - gallery on project page):
   • Names: image1.jpg, image2.jpg, ... image9.jpg
   • Numbering must be consecutive (1, 2, 3...)
   • Supported formats: .jpg, .jpeg, .png, .gif, .svg, .pdf
   • Images appear in order on project page

4. EXAMPLE PROJECT STRUCTURE
   projects/0056/
   ├── title.txt
   ├── description.txt
   ├── hashtags.txt
   ├── icon.svg
   ├── trailer.mp4
   ├── image1.jpg
   ├── image2.jpg
   └── image3.jpg

5. VALIDATE YOUR FILES
   ✓ Folder name is 4+ digits
   ✓ title.txt exists and has content
   ✓ description.txt exists
   ✓ hashtags.txt exists (can be empty)
   ✓ icon.svg/png/jpg exists
   ✓ Images/trailer are named correctly
   ✓ No typos in filenames

6. GENERATE THE SITE
   In terminal, run:
   $ python generate.py

   This will:
   • Create index.html (main grid page)
   • Create projectXXXX.html for each project folder
   • Auto-link projects in sequence (prev/next navigation)

7. TEST LOCALLY
   • Open index.html in browser
   • Test all new project pages
   • Test toggle button (bubble mode)
   • Test filters (#SELECTED, #ARCHITECTURE, etc.)
   • Test responsive design on mobile
   • Test project navigation (prev/next arrows)

8. CHECK GENERATED FILES
   New files created:
   • index.html (updated with all projects)
   • project0056.html (new project page)
   • Any other updated projectXXXX.html files (if needed)

9. REVIEW CHANGES BEFORE PUSHING
   $ git status
   
   You should see:
   ✓ Modified: index.html
   ✓ New: project0056.html
   ✓ Modified: styles.css? (only if you edited it)
   ✗ NOT any .py or internal config files

10. COMMIT AND PUSH
    $ git add .
    $ git commit -m "Add project 0056: [Project Name]"
    $ git push origin main

================================================================================
WORKFLOW FOR EDITING EXISTING PROJECTS
================================================================================

To modify an existing project:
1. Edit the files in projects/XXXX/ (title, description, images, etc.)
2. Run: python generate.py
3. Review changes in browser
4. Commit and push

================================================================================
WORKFLOW FOR EDITING STYLES/FUNCTIONALITY
================================================================================

To modify CSS or JavaScript:
1. Edit styles.css or the inline <script> in index.html
2. Test in browser (no need to run generate.py)
3. Commit and push

Note: Do NOT edit project HTML files directly (projectXXXX.html)
They are auto-generated and will be overwritten when you run generate.py

================================================================================
IMPORTANT NOTES
================================================================================

• The generate.py script is the SOURCE OF TRUTH
  Always modify the projects/ folder, not generated HTML files

• Project numbers should be sequential and unique
  (The system will handle gaps, but avoid duplicate numbers)

• The toggle button switches between:
  - Normal mode (grid layout)
  - Bubble mode (physics-based interactive bubbles)

• Filter buttons work based on hashtags
  Add #selected, #architecture, #tech, #art, #music to projects

• The site is deployed via GitHub Pages
  Make sure all changes are committed before pushing

• Generated index.html and projectXXXX.html files should be committed
  The projects/ folder structure is the source, HTML files are output

================================================================================
TROUBLESHOOTING
================================================================================

Issue: generate.py says "Missing icon"
→ Add icon.svg, icon.png, or icon.jpg to your project folder

Issue: Project doesn't appear on index
→ Folder name must be 4+ digits and only digits (e.g., 0056, not project056)

Issue: Images not showing
→ Check filenames: image1.jpg, image2.jpg (not Image1, img1, etc.)
→ Ensure they're in the correct project folder

Issue: Filter buttons don't work
→ Add hashtags to hashtags.txt file in project folder
→ Use format: #hashtag or #hashtag #hashtag2

Issue: Trailer doesn't play
→ If using .mp4, check file format (must be MP4 video)
→ If using trailer.txt, check embed code syntax

================================================================================
QUICK REFERENCE CHECKLIST
================================================================================

Before running python generate.py:
☐ Project folder created with 4+ digit name
☐ title.txt exists and filled
☐ description.txt exists and filled
☐ hashtags.txt exists (can be empty or have hashtags)
☐ icon.svg/png/jpg exists
☐ Images named image1.jpg, image2.jpg, etc. (consecutive)
☐ Trailer.mp4/gif OR trailer.txt (if needed)

After running python generate.py:
☐ No errors in terminal
☐ index.html looks correct with new project
☐ projectXXXX.html opens and displays correctly
☐ Images/trailer load properly
☐ Navigation arrows work
☐ Filters show project in correct categories

Before pushing to GitHub:
☐ All generated files created (no errors)
☐ Tested in browser locally
☐ git status shows only expected changes
☐ Commit message describes the changes
☐ No sensitive files committed

================================================================================
END OF GUIDE
================================================================================
