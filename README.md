# Supersimple Website

Static portfolio website and local tailored-application generator for Ivan
Bagaturiya. GitHub Pages serves the repository root through the domain in
`CNAME`.

## Repository structure

```text
.
├── index.html                  Generated website index
├── CNAME                       GitHub Pages domain
├── generate.py                 Stable site-generation command
├── assets/
│   ├── css/                    Website styles
│   └── js/                     Browser-side interactions and filters
├── templates/
│   ├── project.html            Template for generated project pages
│   └── about.html              About/CV page template
├── tools/
│   └── site_generator.py       Site-generation implementation
├── projects/
│   ├── NNNN-readable-slug/     Published project sources
│   ├── _drafts/                Unpublished project sources
│   ├── _archive/               Retired project sources
│   └── _template/              Folder to copy for a new project
├── projecthtml/                Generated project pages
├── portfolio-export/           Tailored CV and portfolio PDF generator
├── start-application-generator.py
│                               Private local generator dashboard
├── archive/                    Legacy files retained for reference
└── output/                     Local generated PDFs; ignored by Git
```

## Published project format

Published folders use `NNNN-readable-slug`: four or more leading digits,
followed by an optional lowercase ASCII slug containing only letters, numbers,
and single hyphens. For example, `projects/0062-housing-tool/` is publishable.
Folders beneath `projects/_drafts/` and `projects/_archive/` are ignored.

The numeric prefix is the permanent project ID. Renaming the slug does not
change the generated public page URL, which remains
`projecthtml/project0062.html`. Duplicate IDs and unsafe or malformed direct
project-folder names stop generation with an error.

Each published project can contain:

```text
projects/0062-housing-tool/
├── title.txt
├── titledescription.txt
├── description.txt
├── hashtags.txt
├── skill.txt
├── icon.svg|png|jpg|jpeg|gif
├── trailer.mp4|gif|txt
└── image1.jpg, image2.png, ...
```

Numbered media may also use names such as `0001_plan.png`. Supported project
media include JPG, JPEG, PNG, GIF, MP4, MP3, PDF, and text links.

## Add or update a published project

1. Copy `projects/_template/` to a new folder such as
   `projects/0062-housing-tool/`.
2. Replace its text and media.
3. Add hashtags such as `#selected`, `#architecture`, `#tech`, `#art`, or
   `#music`.
4. List the portfolio skill chips in `skill.txt`, for example
   `#rhino #grasshopper #parametric-design`.
5. Generate the site:

```bash
python3 generate.py
```

6. Open `index.html` through a local web server and verify the index, filters,
   project page, media, and previous/next navigation.

Do not edit generated pages in `projecthtml/` directly. The About/CV page at
`projecthtml/project2409.html` is generated from `templates/about.html` and
`portfolio-export/data/cv.json`.

## Draft and archive workflow

- Put unfinished work in `projects/_drafts/<id>-<slug>/`.
- Move ready work to `projects/<id>/` before generating the site.
- Move retired source material to `projects/_archive/<id>-<slug>/`.
- Legacy generated pages can remain in `projecthtml/` to preserve old direct
  URLs even when they are no longer linked from the index.

## Website source and output

The generator reads project source folders, the page templates, and the main CV
source, then writes:

- `index.html`
- `projecthtml/projectNNNN.html`
- `projecthtml/project2409.html` as the About/CV page
- `assets/downloads/Ivan_Bagaturiya_CV.pdf` as the public comprehensive CV
- `assets/downloads/Ivan_Bagaturiya_Portfolio.pdf` as the public full portfolio

The index embeds each project's hashtags in `data-hashtags`. The filter and
bubble interactions live in `assets/js/site.js`. Matter.js is loaded from a CDN
for the optional physics mode.

The visible filters are Selected, Architecture, Tech, Art, and Fun. Projects
may still use `#music` as metadata even though Music is not a visible filter.

## About/CV page

`portfolio-export/data/cv.json` is the single content source for the public
About/CV page and its downloadable comprehensive PDF. It includes profile text,
contact details, skills, software, experience, education, professors, languages,
and hobbies. Internal verification notes and local source-document paths are not
rendered publicly.

After changing `cv.json`, run `python3 generate.py` to update both the web page
and public CV PDF.

## Tailored PDF exports

The independent `portfolio-export/` tool reads the same published project
library and generates application-specific CV and portfolio PDFs. Full and
tailored portfolios share one layout: cover, contents, project opener and
content pages, followed by the website QR page. Its workflow is documented in
`portfolio-export/README.md`.

To use the private dashboard, install the PDF dependencies once and start it:

```bash
python3 -m pip install -r portfolio-export/requirements.txt
python3 start-application-generator.py
```

The dashboard opens at `http://127.0.0.1:8765/`. Paste a vacancy, preview the
ranked projects, adjust the selection, and generate both PDFs. The server binds
only to this Mac; it is not part of the public GitHub Pages website. Stop it
with `Control-C` in the terminal.

## Archives

`archive/legacy-styles/` contains unused historical CSS. It is not referenced by
the live website. Keep new archival material out of the root and active project
folders.
