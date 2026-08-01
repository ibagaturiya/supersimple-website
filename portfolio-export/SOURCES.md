# PDF and CV source map

The PDFs are generated from structured data and the existing project library.
There is no stored PDF cover page or editable PDF template.

## Portfolio cover

| Visible item | Source |
|---|---|
| Name | `data/cv.json` -> `name` |
| Initials | `data/cv.json` -> `initials` |
| Subtitle | `data/cv.json` -> `headline` |
| Target office | Application-generator form -> Office |
| Target position | Application-generator form -> Position |
| Portrait | `projects/2409-about/image1.png` |
| Cover composition, colors and type sizes | `generate.py` -> `render_portfolio()` |

Replacing `projects/2409-about/image1.png` changes the cover portrait. Keep the
same filename and use a sufficiently large image. The generator crops it to the
right-hand portrait area.

## CV content

All factual CV content is in `data/cv.json`.

| Content | JSON field |
|---|---|
| Name and subtitle | `name`, `initials`, `headline` |
| Contact details | `contact` |
| Main profile paragraph | `profile` |
| General CV skills and software | `skill_groups` |
| Work history | `experience` |
| Education and professors | `education` |
| Languages | `languages` |
| Hobbies | `hobbies` |

The current PDF uses `profile`. The additional `profile_de` and `profile_en`
fields are stored for later language switching but are not selected
automatically yet.

Relevant skill groups and individual items move upward based on the target
vacancy. Their wording is never rewritten.

## Project title, text and tags

Every published project has its own folder, for example
`projects/0051-the-cabrio/`.

| Content | Source |
|---|---|
| Project title | `title.txt` |
| Project description | `description.txt` |
| Website tags | `hashtags.txt` |
| Website icon and trailer | `icon.*`, `trailer.*` |
| Website media | numbered image/media files |

`titledescription.txt`, the icon, and the trailer are used by the website, not
by the portfolio PDF.

## Project export metadata

Project-specific PDF settings are in `data/projects.json`, keyed by the stable
four-digit project ID.

```json
"0051": {
  "year": "2024",
  "tags": ["architecture", "computational design"],
  "software": ["Rhino", "Grasshopper"],
  "skills": ["architectural design", "parametric design"],
  "priority": 4,
  "images": ["image2.jpeg", "image4.jpeg", "image5.jpeg"]
}
```

- `software`: software demonstrated by this specific project.
- `skills`: skills demonstrated by this specific project.
- `tags`: project topics used for matching and displayed as chips.
- `priority`: a small base ranking bonus. Higher values favor a project.
- `images`: preferred project images in priority order.
- `exclude: true`: keeps a published website project out of PDF selection.

Only add software and skills that the project genuinely demonstrates.

## How the two project images are chosen

For each selected project, the generator reads `images` from
`data/projects.json`. It checks those filenames inside the matching project
folder and uses the first two existing images.

If `images` is missing or empty, the generator automatically finds files whose
names begin with `image`, sorts them by their number, and uses the first two.

- Two available images: stacked vertically.
- One available image: fills the complete image area.
- No available image: a neutral placeholder is shown.

Reorder the `images` list to change which image appears first. The third and
later entries are fallbacks and are not currently placed on the project page.

## Text length and cutting

The portfolio uses a fixed one-page layout per project. In `generate.py`, the
project description is currently limited to 15 lines. Longer text receives an
ellipsis so it cannot overlap the images or footer.

Other fixed limits include:

- Project title: 2 lines.
- CV profile: 9 lines.
- Several compact CV entries: 1 or 2 lines.

For best results, edit each project's `description.txt` into a concise portfolio
description. Removing the limits or adding continuation pages requires a layout
change in `generate.py` rather than a data change.

## Ranking explanations

Match reasons and scores remain in the generated `selection.json` for private
review. They are not printed in the applicant-facing portfolio.

## Generated files

Each application package is written under `output/pdf/<office-position>/`:

- `Ivan_Bagaturiya_Portfolio.pdf`
- `Ivan_Bagaturiya_CV.pdf`
- `application.json`
- `selection.json`

The JSON files preserve the inputs and ranking decisions used for that export.
Do not edit generated PDFs directly; update the sources above and generate them
again.
