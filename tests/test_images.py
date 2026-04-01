"""Tests for echotrail_gen.images – image resizing and thumbnail generation."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from echotrail_gen.images import (
    resize_image,
    thumb_name,
    process_entry_media,
    WEB_MAX_PX,
    THUMB_MAX_PX,
)


def _create_test_jpeg(path: Path, width: int = 3000, height: int = 2000) -> None:
    """Create a real JPEG image at *path*."""
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="JPEG", quality=90)


class TestThumbName:
    def test_jpg(self):
        assert thumb_name("foto.jpg") == "thumb_foto.jpg"

    def test_png(self):
        assert thumb_name("landscape.png") == "thumb_landscape.jpg"

    def test_preserves_stem(self):
        assert thumb_name("my-image.jpeg") == "thumb_my-image.jpg"


class TestResizeImage:
    def test_downscales_large_image(self, tmp_path: Path):
        src = tmp_path / "big.jpg"
        dst = tmp_path / "out.jpg"
        _create_test_jpeg(src, 4000, 3000)

        resize_image(src, dst, WEB_MAX_PX, 82)

        with Image.open(dst) as img:
            assert max(img.size) <= WEB_MAX_PX

    def test_small_image_stays_within_bounds(self, tmp_path: Path):
        src = tmp_path / "small.jpg"
        dst = tmp_path / "out.jpg"
        _create_test_jpeg(src, 800, 600)

        resize_image(src, dst, WEB_MAX_PX, 82)

        with Image.open(dst) as img:
            assert max(img.size) <= WEB_MAX_PX

    def test_thumbnail_size(self, tmp_path: Path):
        src = tmp_path / "big.jpg"
        dst = tmp_path / "thumb.jpg"
        _create_test_jpeg(src, 3000, 2000)

        resize_image(src, dst, THUMB_MAX_PX, 75)

        with Image.open(dst) as img:
            assert max(img.size) <= THUMB_MAX_PX


class TestProcessEntryMedia:
    def test_creates_web_and_thumb(self, tmp_path: Path):
        src = tmp_path / "src_media"
        dst = tmp_path / "dst_media"
        src.mkdir()
        _create_test_jpeg(src / "photo.jpg", 3000, 2000)

        process_entry_media(src, dst)

        assert (dst / "photo.jpg").exists()
        assert (dst / "thumb_photo.jpg").exists()

        with Image.open(dst / "photo.jpg") as img:
            assert max(img.size) <= WEB_MAX_PX
        with Image.open(dst / "thumb_photo.jpg") as img:
            assert max(img.size) <= THUMB_MAX_PX

    def test_copies_video_unchanged(self, tmp_path: Path):
        src = tmp_path / "src_media"
        dst = tmp_path / "dst_media"
        src.mkdir()
        (src / "clip.mp4").write_bytes(b"\x00\x00fake-mp4-data")

        process_entry_media(src, dst)

        assert (dst / "clip.mp4").exists()
        assert (dst / "clip.mp4").read_bytes() == b"\x00\x00fake-mp4-data"
        # No thumbnail for videos
        assert not (dst / "thumb_clip.jpg").exists()

    def test_excludes_video_when_requested(self, tmp_path: Path):
        src = tmp_path / "src_media"
        dst = tmp_path / "dst_media"
        src.mkdir()
        (src / "clip.mp4").write_bytes(b"\x00\x00fake-mp4-data")

        process_entry_media(src, dst, skip_videos=True)

        assert not (dst / "clip.mp4").exists()

    def test_skips_dotfiles(self, tmp_path: Path):
        src = tmp_path / "src_media"
        dst = tmp_path / "dst_media"
        src.mkdir()
        (src / ".gitkeep").write_text("")

        process_entry_media(src, dst)

        assert not (dst / ".gitkeep").exists()

    def test_nonexistent_src(self, tmp_path: Path):
        dst = tmp_path / "dst_media"
        # Should not raise
        process_entry_media(tmp_path / "nope", dst)
        assert not dst.exists()

    def test_multiple_images(self, tmp_path: Path):
        src = tmp_path / "src_media"
        dst = tmp_path / "dst_media"
        src.mkdir()
        _create_test_jpeg(src / "a.jpg", 2000, 1500)
        _create_test_jpeg(src / "b.png", 1800, 1200)

        process_entry_media(src, dst)

        assert (dst / "a.jpg").exists()
        assert (dst / "thumb_a.jpg").exists()
        assert (dst / "b.png").exists()
        assert (dst / "thumb_b.jpg").exists()
