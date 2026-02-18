#!/usr/bin/env python3
"""
Image Compression for Website Serving
Creates compressed versions in 'projects-optimized/' folder.
Originals stay untouched in 'projects/' folder.

Usage:
  python3 build_optimized.py 50    (compression level 0-100)
  python3 build_optimized.py 80
"""

import os
import sys
import shutil
from pathlib import Path
from PIL import Image

# ============================================================================
# COMPRESSION LEVEL PRESETS (0-100)
# ============================================================================

def get_settings(compression_level):
    """Convert compression level (0-100) to actual settings."""
    level = max(0, min(100, compression_level))
    
    jpeg_quality = 90 - int((level / 100) * 40)  # 90 down to 50
    png_compression = 4 + int((level / 100) * 5)  # 4 to 9
    max_size = 2560 - int((level / 100) * 1760)   # 2560 down to 800
    
    return {
        'jpeg_quality': jpeg_quality,
        'png_compression': png_compression,
        'max_width': max_size,
        'max_height': max_size,
        'gif_max_width': max(600, max_size - 300),
        'gif_max_height': max(600, max_size - 300),
    }

# ============================================================================

def get_file_size_mb(filepath):
    """Get file size in MB."""
    return os.path.getsize(filepath) / (1024 * 1024)

def optimize_image(input_path, output_path, settings):
    """
    Optimize a single image.
    Returns tuple: (success, original_size_mb, new_size_mb, message)
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if not input_path.exists():
        return False, 0, 0, f"File not found"
    
    original_size = get_file_size_mb(input_path)
    
    try:
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Open image
        img = Image.open(input_path)
        
        # Convert RGBA to RGB if saving as JPEG
        if output_path.suffix.lower() in ['.jpg', '.jpeg'] and img.mode == 'RGBA':
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3])
            img = rgb_img
        
        # Determine max dimensions based on file type
        if output_path.suffix.lower() == '.gif':
            max_w = settings['gif_max_width']
            max_h = settings['gif_max_height']
        else:
            max_w = settings['max_width']
            max_h = settings['max_height']
        
        # Resize if too large
        resized_msg = ""
        if img.width > max_w or img.height > max_h:
            img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            resized_msg = " (resized)"
        
        # Save with compression
        if output_path.suffix.lower() in ['.jpg', '.jpeg']:
            img.save(output_path, 'JPEG', quality=settings['jpeg_quality'], optimize=True)
        elif output_path.suffix.lower() == '.png':
            img.save(output_path, 'PNG', compress_level=settings['png_compression'], optimize=True)
        elif output_path.suffix.lower() == '.gif':
            img.save(output_path, 'GIF', optimize=True)
        else:
            return False, original_size, 0, f"Unsupported format"
        
        new_size = get_file_size_mb(output_path)
        reduction = ((original_size - new_size) / original_size * 100) if original_size > 0 else 0
        
        return True, original_size, new_size, f"{reduction:.1f}%{resized_msg}"
        
    except Exception as e:
        return False, original_size, 0, f"Error: {str(e)}"

def main():
    """Create optimized versions of all project files."""
    
    if len(sys.argv) < 2:
        print("Usage: python3 generate.py <compression_level>")
        print("\nCompression levels:")
        print("  0   - No compression (original quality, largest files)")
        print("  30  - Light compression")
        print("  50  - Balanced (recommended)")
        print("  80  - Aggressive compression")
        print("  100 - Maximum compression")
        print("\nExamples:")
        print("  python3 generate.py 50")
        print("  python3 generate.py 80")
        return
    
    try:
        compression_level = int(sys.argv[1])
    except ValueError:
        print(f"❌ Invalid compression level: {sys.argv[1]}")
        return
    
    settings = get_settings(compression_level)
    
    source_dir = Path(__file__).parent / "projects"
    output_dir = Path(__file__).parent / "projects-optimized"
    
    if not source_dir.exists():
        print(f"❌ Source folder not found: {source_dir}")
        return
    
    # Clear output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()
    
    print("=" * 80)
    print(f"BUILDING OPTIMIZED IMAGES - Compression Level {compression_level}/100")
    print("=" * 80)
    print(f"\nSettings:")
    print(f"  • JPEG quality: {settings['jpeg_quality']}/100")
    print(f"  • PNG compression: {settings['png_compression']}/9")
    print(f"  • Max dimensions: {settings['max_width']}x{settings['max_height']}px")
    print(f"\nSource: {source_dir}")
    print(f"Output: {output_dir}")
    print("\n" + "-" * 80 + "\n")
    
    # Find all files (images + metadata)
    all_files = list(source_dir.rglob("*"))
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    
    total_original = 0
    total_new = 0
    successful = 0
    failed = 0
    
    for filepath in sorted(all_files):
        if not filepath.is_file():
            continue
        
        rel_path = filepath.relative_to(source_dir)
        output_path = output_dir / rel_path
        
        # For images: optimize
        if filepath.suffix.lower() in image_extensions:
            success, orig_size, new_size, msg = optimize_image(filepath, output_path, settings)
            
            if success:
                successful += 1
                total_original += orig_size
                total_new += new_size
                status = "✅"
            else:
                failed += 1
                status = "❌"
            
            print(f"{status} {rel_path}")
            print(f"    {orig_size:.2f}MB → {new_size:.2f}MB ({msg})")
        else:
            # For other files (metadata, etc): just copy
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(filepath, output_path)
            print(f"📄 {rel_path}")
    
    # Summary
    print("\n" + "=" * 80)
    print("BUILD COMPLETE")
    print("=" * 80)
    print(f"✅ Images optimized: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📄 Files copied: {len(all_files) - successful - failed}")
    
    if total_original > 0:
        total_reduction = ((total_original - total_new) / total_original * 100)
        print(f"\nImage compression:")
        print(f"  • Before: {total_original:.2f}MB")
        print(f"  • After:  {total_new:.2f}MB")
        print(f"  • Saved: {total_reduction:.1f}%")
    
    print(f"\n✅ Ready to use: projects-optimized/")
    print("   Update your HTML to reference: projects-optimized/ instead of projects/")
    print("\n")

if __name__ == "__main__":
    main()
