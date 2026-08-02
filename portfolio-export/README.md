# Tailored portfolio and CV export

This add-on reads the existing `projects/NNNN-readable-slug/` library and generates a ranked,
role-specific portfolio PDF and CV PDF. It is deliberately separate from the
website generator, so it does not rewrite `index.html`, project pages, styles, or
JavaScript.

See `SOURCES.md` for the complete map of every editable CV, cover, portrait,
project-text, image, software, and skill source.

The public comprehensive CV used by the About page and the canonical full
portfolio are generated with the normal site command:

```bash
python3 generate.py
```

It writes:

- `assets/downloads/Ivan_Bagaturiya_CV.pdf`
- `portfolio.html`, containing every publishable project
- `assets/downloads/Ivan_Bagaturiya_Portfolio.pdf`, printed from `portfolio.html`
- `assets/downloads/Ivan_Bagaturiya_Full_CV_and_Portfolio.zip`, containing both
  complete PDFs for the About-page download

The full and tailored portfolios share
`portfolio-export/templates/portfolio.html` and
`portfolio-export/templates/portfolio.css`. Change these files to adjust the
portfolio layout globally. Tailored exports change the project selection and
cover text, but not the layout system. Portfolio pages 2 and 3 render the CV
directly from `data/cv.json` as full-size rounded cards; the selected-project
contents starts on page 4. The cover artwork comes from
`assets/titlepageimage/titlepagemage.png`.

Every published project has a `skill.txt`. Write hash-prefixed labels there,
such as `#rhino #grasshopper`; those values become the outlined skill chips on
the project's opener and are also used by the tailored-project matcher. The
Areal Archive keeps the same opener, then uses its complete image set as one
edge-to-edge contact sheet. Every project image is included: the first image is
reserved for the full-height opener, paired body pages are vertically centered,
and the final body page is a single full-bleed image. Every media item displays
its source filename without the extension. Numbered `.txt` files that are not
project metadata participate in the same natural filename order as images and
are typeset as justified text-media panels.

The public CV contains the
full verified profile, experience highlights, education and professors,
languages, skills, software, and hobbies. Internal verification notes and local
source-document paths are excluded.

## One-time setup

From the repository root:

```bash
python3 -m pip install -r portfolio-export/requirements.txt
```

## Generate from an application profile

### Private dashboard

From the repository root, start the local interface:

```bash
python3 start-application-generator.py
```

It opens `http://127.0.0.1:8765/`. Enter the office and role, paste the vacancy,
and select **Preview match**. The dashboard shows automatically detected terms,
project scores, and the reasons for each match. Check or uncheck projects before
selecting **Generate CV + Portfolio**.

The dashboard is deliberately local-only and is not deployed with GitHub Pages.
Each export saves `application.json` and `selection.json` beside the two PDFs so
the exact input and selection remain reviewable.

### Command line

Duplicate the example application JSON, paste the vacancy into
`job_description`, and adjust the structured software/skill/focus lists:

```bash
python3 portfolio-export/generate.py \
  portfolio-export/applications/example-computational-architecture.json
```

The files are written to `output/pdf/<office-position>/`:

- `Ivan_Bagaturiya_Portfolio.pdf`
- `Ivan_Bagaturiya_Portfolio.html`
- `Ivan_Bagaturiya_CV.pdf`
- `selection.json` (scores and match reasons for review)

You can also drop in a plain text vacancy:

```bash
python3 portfolio-export/generate.py vacancy.txt \
  --office "Office Name" \
  --position "Architect" \
  --software "Vectorworks,Rhino" \
  --skills "architectural design,execution planning"
```

Known software, skill, and focus phrases are detected automatically in pasted
vacancy text. The optional flags are useful when an office's needs are implied
rather than written explicitly.

Hobbies are stored as an optional CV module and are included by default. Choose
the categories and maximum number of entries for an application with:

```json
"include_hobbies": true,
"hobby_categories": ["Fotografie", "Musik"],
"hobby_item_limit": 4
```

An empty `hobby_categories` list allows every category. The generator distributes
the available space across the selected categories. For a plain-text vacancy,
use `--hobby-categories "Fotografie,Musik"`. Disable hobbies for one application
with `"include_hobbies": false` or the `--no-hobbies` command-line option.

## Truth and tailoring layers

- `projects/NNNN-readable-slug/`: existing website source; titles, descriptions, hashtags,
  and images are reused directly.
- `portfolio-export/data/projects.json`: optional export-only metadata such as
  software, skills, priority, and year. Portfolio images always follow the
  natural filename order from each project folder.
- `portfolio-export/data/cv.json`: verified CV facts and reusable skill modules.
- `portfolio-export/applications/*.json`: one target office/position per file.

The ranking is deterministic. Structured software matches have the highest
weight, followed by skills, focus/tags, job-text keywords, and project priority.
The generator records every score and match reason in `selection.json`. It never
creates experience, dates, software proficiency, or other CV facts that are not
in `cv.json`.

## Project-folder behavior

Both generators accept published direct children named
`NNNN-readable-lowercase-slug`. The numeric prefix remains the project ID and
the slug is only for human readability. Drafts and archives remain outside the
published library under `projects/_drafts/` and `projects/_archive/`.

Malformed direct folders and duplicate numeric IDs stop generation instead of
being silently skipped.

Before sending a real application, complete and verify the empty experience,
language, dates, location, and proficiency fields in `data/cv.json`.
