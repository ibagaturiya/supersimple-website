#!/usr/bin/env python3
"""
Optimize JPEG images in `projects/` by resizing and recompressing.

Default behavior is a dry run. Change options at the top or pass CLI flags.

Usage:
  python3 tools/optimize_images.py --dry-run
  python3 tools/optimize_images.py --max-width 1200 --quality 75 --backup
"""
from __future__ import annotations
import argparse
import os
import sys
import shutil
from pathlib import Path
try:
    from PIL import Image
except Exception:
    print("Pillow is required. Install with: pip install pillow")
    sys.exit(1)

DEFAULT_MAX_WIDTH = 1200
DEFAULT_MAX_HEIGHT = 1200
DEFAULT_QUALITY = 75

SUPPORTED_JPEG = {".jpg", ".jpeg"}
SUPPORTED_PNG = {".png"}


def find_images(root: Path):
    for p in root.rglob('*'):
        if p.suffix.lower() in SUPPORTED_JPEG.union(SUPPORTED_PNG):
            yield p


def optimize_jpeg(path: Path, max_w: int, max_h: int, quality: int, backup: bool, dry_run: bool):
    img = Image.open(path)
    orig = img.size
    img.thumbnail((max_w, max_h), Image.LANCZOS)

    if dry_run:
        return (str(path), orig, img.size, 'would-write')

    if backup:
        bak = path.with_suffix(path.suffix + '.bak')
        if not bak.exists():
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, bak)

    # Ensure RGB for JPEG
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        out = bg
    else:
        out = img.convert('RGB')

    out.save(path, format='JPEG', quality=quality, optimize=True, progressive=True)
    return (str(path), orig, out.size, 'written')


def convert_png_to_webp(path: Path, max_w: int, max_h: int, quality: int, backup: bool, dry_run: bool):
    img = Image.open(path)
    orig = img.size
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    out_path = path.with_suffix('.webp')

    if dry_run:
        return (str(path), orig, img.size, f'would-write:{out_path.name}')

    if backup:
        bak = path.with_suffix(path.suffix + '.bak')
        if not bak.exists():
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, bak)

    img.save(out_path, 'WEBP', quality=quality, method=6)
    return (str(path), orig, img.size, f'written:{out_path.name}')


def main():
    ap = argparse.ArgumentParser(description="Optimize images under projects/")
    ap.add_argument('--root', default='projects', help='Root folder to scan')
    ap.add_argument('--max-width', type=int, default=DEFAULT_MAX_WIDTH)
    ap.add_argument('--max-height', type=int, default=DEFAULT_MAX_HEIGHT)
    ap.add_argument('--quality', type=int, default=DEFAULT_QUALITY, help='JPEG/WEBP quality (0-100)')
    ap.add_argument('--convert-png-webp', action='store_true', help='Also convert PNGs to WebP')
    ap.add_argument('--backup', action='store_true', help='Keep a .bak copy of each file before overwriting')
    ap.add_argument('--dry-run', action='store_true', default=True, help='Do not modify files; show actions (default: true)')
    ap.add_argument('--no-dry-run', dest='dry_run', action='store_false', help='Actually write changes')

    args = ap.parse_args()
    root = Path(args.root)

    if not root.exists():
        print(f'Root folder not found: {root}')
        sys.exit(2)

    files = list(find_images(root))
    if not files:
        print('No images found under', root)
        return

    summary = []
    for p in files:
        suf = p.suffix.lower()
        try:
            if suf in SUPPORTED_JPEG:
                res = optimize_jpeg(p, args.max_width, args.max_height, args.quality, args.backup, args.dry_run)
            elif suf in SUPPORTED_PNG:
                if args.convert_png_webp:
                    res = convert_png_to_webp(p, args.max_width, args.max_height, args.quality, args.backup, args.dry_run)
                else:
                    # skip PNG unless converting
                    res = (str(p), 'skipped', 'skipped', 'png-skip')
            else:
                res = (str(p), 'unknown', 'unknown', 'skipped')
        except Exception as e:
            res = (str(p), 'error', str(e), 'error')
        summary.append(res)

    # print results
    for row in summary:
        print('\t'.join(map(str, row)))

    # quick stats
    written = [r for r in summary if r[3].startswith('written')]
    would = [r for r in summary if 'would' in r[3]]
    skipped = [r for r in summary if 'skip' in r[3]]
    print(f'Found: {len(files)} images — to-write: {len(would)}; written: {len(written)}; skipped: {len(skipped)}')


if __name__ == '__main__':
    main()
