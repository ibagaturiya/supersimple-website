# Tailored portfolio and CV export

This add-on reads the existing `projects/NNNN/` library and generates a ranked,
role-specific portfolio PDF and CV PDF. It is deliberately separate from the
website generator, so it does not rewrite `index.html`, project pages, styles, or
JavaScript.

## One-time setup

From the repository root:

```bash
python3 -m pip install -r portfolio-export/requirements.txt
```

## Generate from an application profile

Duplicate the example application JSON, paste the vacancy into
`job_description`, and adjust the structured software/skill/focus lists:

```bash
python3 portfolio-export/generate.py \
  portfolio-export/applications/example-computational-architecture.json
```

The files are written to `output/pdf/<office-position>/`:

- `Ivan_Bagaturiya_Portfolio.pdf`
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

- `projects/NNNN/`: existing website source; titles, descriptions, hashtags,
  and images are reused directly.
- `portfolio-export/data/projects.json`: optional export-only metadata such as
  software, skills, priority, year, and preferred portfolio images.
- `portfolio-export/data/cv.json`: verified CV facts and reusable skill modules.
- `portfolio-export/applications/*.json`: one target office/position per file.

The ranking is deterministic. Structured software matches have the highest
weight, followed by skills, focus/tags, job-text keywords, and project priority.
The generator records every score and match reason in `selection.json`. It never
creates experience, dates, software proficiency, or other CV facts that are not
in `cv.json`.

## Important current-library behavior

The website accepts only project folder names containing 4 or more digits.
The export tool intentionally applies the same rule. Therefore
`projects/0058 lamp v1/` and `projects/0059 beamboxmap/` are not loaded by either
system. Rename them to `0058` and `0059` only after checking that they are ready
to publish.

Before sending a real application, complete and verify the empty experience,
language, dates, location, and proficiency fields in `data/cv.json`.
