"""Tests for the image processing module."""

from __future__ import annotations

import pytest

from prezo.images import process_slide_images, resolve_image_path
from prezo.parser import ImageRef, Slide


class TestResolveImagePath:
    """Tests for resolve_image_path function."""

    def test_absolute_path_exists(self, tmp_path):
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake image")

        result = resolve_image_path(str(img_path), None)
        assert result == img_path

    def test_absolute_path_not_exists(self):
        result = resolve_image_path("/nonexistent/path/image.png", None)
        assert result is None

    def test_relative_path_with_presentation(self, tmp_path):
        # Create image file
        img_path = tmp_path / "images" / "test.png"
        img_path.parent.mkdir()
        img_path.write_bytes(b"fake image")

        # Create presentation file
        pres_path = tmp_path / "slides.md"
        pres_path.write_text("# Test")

        result = resolve_image_path("images/test.png", pres_path)
        assert result == img_path

    def test_relative_path_without_presentation(self, tmp_path):
        result = resolve_image_path("nonexistent.png", None)
        assert result is None

    def test_http_url_returns_none(self):
        result = resolve_image_path("http://example.com/image.png", None)
        assert result is None

    def test_https_url_returns_none(self):
        result = resolve_image_path("https://example.com/image.png", None)
        assert result is None

    def test_data_url_returns_none(self):
        result = resolve_image_path("data:image/png;base64,abc123", None)
        assert result is None


class TestProcessSlideImages:
    """Tests for process_slide_images function."""

    def test_slide_without_images_unchanged(self):
        slide = Slide(content="# No images here", index=0)
        result = process_slide_images(slide, None)
        assert result == "# No images here"

    def test_slide_with_unresolvable_image_shows_placeholder(self):
        slide = Slide(
            content="# Title\n\n![Test Image](nonexistent.png)\n\nText",
            index=0,
            images=[
                ImageRef(
                    alt="Test Image",
                    path="nonexistent.png",
                    start=10,
                    end=39,
                )
            ],
        )
        result = process_slide_images(slide, None)
        assert "[Image: Test Image]" in result
        assert "![Test Image]" not in result

    def test_multiple_images_processed(self):
        content = "![First](a.png)\n\n![Second](b.png)"
        slide = Slide(
            content=content,
            index=0,
            images=[
                ImageRef(alt="First", path="a.png", start=0, end=15),
                ImageRef(alt="Second", path="b.png", start=17, end=33),
            ],
        )
        result = process_slide_images(slide, None)
        assert "[Image: First]" in result
        assert "[Image: Second]" in result

    def test_image_with_empty_alt_uses_default(self):
        slide = Slide(
            content="![](image.png)",
            index=0,
            images=[ImageRef(alt="", path="image.png", start=0, end=14)],
        )
        result = process_slide_images(slide, None)
        assert "[Image: image]" in result


class TestProcessSlideWithRealImage:
    """Tests for process_slide_images with actual image files."""

    @pytest.fixture
    def simple_image(self, tmp_path):
        """Create a simple test image."""
        try:
            from PIL import Image

            img = Image.new("RGB", (100, 100), color="red")
            path = tmp_path / "test.png"
            img.save(path)
            return path
        except ImportError:
            pytest.skip("PIL not available")

    def test_renders_existing_image(self, tmp_path, simple_image):
        pres_path = tmp_path / "slides.md"
        pres_path.write_text("# Test")

        content = "# Title\n\n![Photo](test.png)"
        # Calculate positions for test.png reference
        start = content.find("![Photo]")
        end = content.find(")") + 1

        slide = Slide(
            content=content,
            index=0,
            images=[ImageRef(alt="Photo", path="test.png", start=start, end=end)],
        )

        result = process_slide_images(slide, pres_path, width=20, height=10)

        # Should contain rendered ASCII art in a code block
        assert "```" in result
        assert "# Title" in result
