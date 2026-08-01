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
│   └── project.html            Template for generated project pages
├── tools/
│   └── site_generator.py       Site-generation implementation
├── projects/
│   ├── NNNN/                   Published project sources
│   ├── _drafts/                Unpublished project sources
│   ├── _archive/               Retired project sources
│   └── _template/              Folder to copy for a new project
├── projecthtml/                Generated project pages
├── portfolio-export/           Tailored CV and portfolio PDF generator
├── archive/                    Legacy files retained for reference
└── output/                     Local generated PDFs; ignored by Git
```

## Published project format

Only direct children of `projects/` whose names contain four or more digits are
published. For example, `projects/0062/` is publishable; folders beneath
`projects/_drafts/` and `projects/_archive/` are ignored.

Each published project can contain:

```text
projects/0062/
├── title.txt
├── titledescription.txt
├── description.txt
├── hashtags.txt
├── icon.svg|png|jpg|jpeg|gif
├── trailer.mp4|gif|txt
└── image1.jpg, image2.png, ...
```

Numbered media may also use names such as `0001_plan.png`. Supported project
media include JPG, JPEG, PNG, GIF, MP4, MP3, PDF, and text links.

## Add or update a published project

1. Copy `projects/_template/` to a new numeric folder such as `projects/0062/`.
2. Replace its text and media.
3. Add hashtags such as `#selected`, `#architecture`, `#tech`, `#art`, or
   `#music`.
4. Generate the site:

```bash
python3 generate.py
```

5. Open `index.html` through a local web server and verify the index, filters,
   project page, media, and previous/next navigation.

Do not edit generated pages in `projecthtml/` directly. The exception is
`projecthtml/project2409.html`, the custom about page, which the generator
intentionally preserves.

## Draft and archive workflow

- Put unfinished work in `projects/_drafts/<id>-<slug>/`.
- Move ready work to `projects/<id>/` before generating the site.
- Move retired source material to `projects/_archive/<id>-<slug>/`.
- Legacy generated pages can remain in `projecthtml/` to preserve old direct
  URLs even when they are no longer linked from the index.

## Website source and output

The generator reads project source folders and `templates/project.html`, then
writes:

- `index.html`
- `projecthtml/projectNNNN.html`

The index embeds each project's hashtags in `data-hashtags`. The filter and
bubble interactions live in `assets/js/site.js`. Matter.js is loaded from a CDN
for the optional physics mode.

## Tailored PDF exports

The independent `portfolio-export/` tool reads the same published project
library and generates application-specific CV and portfolio PDFs. Its workflow
is documented in `portfolio-export/README.md`.

## Archives

`archive/legacy-styles/` contains unused historical CSS. It is not referenced by
the live website. Keep new archival material out of the root and active project
folders.

