"""Image processing: resize originals for web and generate thumbnails."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)

# Maximum dimension (width or height) for each variant.
# Web-sized images are optimized for modern displays while keeping file size reasonable
# (typically ~200-300KB for 1600px images with quality=82).
WEB_MAX_PX = 1600

# Thumbnails are used in gallery grids and should be small and fast-loading
# (typically <50KB at 400px with quality=75).
THUMB_MAX_PX = 400

# JPEG quality settings (0-100, where higher = better quality but larger files).
# 82 provides excellent visual quality with good compression for full-sized images.
WEB_QUALITY = 82

# Lower quality is acceptable for thumbnails since they're displayed small.
# 75 provides sufficient quality while minimizing load times in galleries.
THUMB_QUALITY = 75

# Resampling filter for high-quality downscaling.
# LANCZOS provides the sharpest results but is slower than simpler filters like BILINEAR.
# Trade-off: Better visual quality is worth the extra processing time for static site generation.
RESIZE_FILTER = Image.LANCZOS

# Extensions handled by Pillow for resizing.
_RESIZABLE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _needs_resize(img: Image.Image, max_px: int) -> bool:
    """Return True if either dimension exceeds *max_px*."""
    return max(img.size) > max_px


def resize_image(src: Path, dst: Path, max_px: int, quality: int) -> None:
    """Resize *src* so the longest side is at most *max_px* and save to *dst*.

    If the image is already within bounds it is saved with re-compression
    only (to normalize quality).  EXIF orientation is honoured.
    """
    with Image.open(src) as img:
        img = img.convert("RGB")
        if _needs_resize(img, max_px):
            img.thumbnail((max_px, max_px), RESIZE_FILTER)
        dst.parent.mkdir(parents=True, exist_ok=True)
        img.save(dst, format="JPEG", quality=quality, optimize=True)


def thumb_name(original: str) -> str:
    """Return the thumbnail filename for *original*."""
    p = Path(original)
    return f"thumb_{p.stem}.jpg"


def process_entry_media(src_dir: Path, dst_dir: Path) -> None:
    """Copy media from *src_dir* to *dst_dir*, resizing images.

    For each image file:
    - ``<name>``  → web-sized JPEG (max 1600 px)
    - ``thumb_<stem>.jpg`` → thumbnail JPEG (max 400 px)

    Non-image files (videos) are copied unchanged.
    """
    if not src_dir.is_dir():
        return

    dst_dir.mkdir(parents=True, exist_ok=True)

    for src_file in sorted(src_dir.iterdir()):
        if src_file.name.startswith("."):
            continue

        ext = src_file.suffix.lower()

        if ext in _RESIZABLE_EXTS:
            # Web-sized version (keep original filename but as JPEG)
            web_dst = dst_dir / src_file.name
            try:
                resize_image(src_file, web_dst, WEB_MAX_PX, WEB_QUALITY)
            except Exception as exc:
                log.warning("Could not resize %s: %s – copying original", src_file, exc)
                shutil.copy2(src_file, web_dst)

            # Thumbnail
            tn = dst_dir / thumb_name(src_file.name)
            try:
                resize_image(src_file, tn, THUMB_MAX_PX, THUMB_QUALITY)
            except Exception as exc:
                log.warning("Could not create thumbnail for %s: %s", src_file, exc)
                # Note: No fallback for thumbnails - gallery will handle missing thumbs
        else:
            # Videos and other files: copy unchanged
            shutil.copy2(src_file, dst_dir / src_file.name)
