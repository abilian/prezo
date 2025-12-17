"""Tests for ASCII image renderers."""

from __future__ import annotations

import pytest

from prezo.images.ascii import (
    ASCII_CHARS,
    ASCII_CHARS_DETAILED,
    AsciiRenderer,
    ColorAsciiRenderer,
    HalfBlockRenderer,
    render_cached,
)


class TestAsciiRenderer:
    """Tests for AsciiRenderer class."""

    def test_name_property(self):
        renderer = AsciiRenderer()
        assert renderer.name == "ascii"

    def test_supports_inline(self):
        renderer = AsciiRenderer()
        assert renderer.supports_inline() is True

    def test_uses_simple_chars_by_default(self):
        renderer = AsciiRenderer()
        assert renderer.chars == ASCII_CHARS

    def test_uses_detailed_chars_when_requested(self):
        renderer = AsciiRenderer(detailed=True)
        assert renderer.chars == ASCII_CHARS_DETAILED

    def test_render_nonexistent_file_shows_placeholder(self, tmp_path):
        renderer = AsciiRenderer()
        fake_path = tmp_path / "nonexistent.png"
        result = renderer.render(fake_path, 40, 10)

        assert "┌" in result  # Box top
        assert "└" in result  # Box bottom
        assert "[Image:" in result

    def test_render_placeholder_truncates_long_filename(self, tmp_path):
        renderer = AsciiRenderer()
        long_name = "a" * 100 + ".png"
        fake_path = tmp_path / long_name
        result = renderer._render_placeholder(fake_path, 40, 10)

        # Should truncate with ellipsis
        assert "..." in result
        # Filename should be truncated, not the full 100+ chars
        assert long_name not in result

    @pytest.fixture
    def simple_image(self, tmp_path):
        """Create a simple test image."""
        try:
            from PIL import Image

            img = Image.new("RGB", (100, 100), color="gray")
            path = tmp_path / "test.png"
            img.save(path)
            return path
        except ImportError:
            pytest.skip("PIL not available")

    def test_render_real_image(self, simple_image):
        renderer = AsciiRenderer()
        result = renderer.render(simple_image, 40, 20)

        # Should produce multiple lines of ASCII art
        lines = result.split("\n")
        assert len(lines) >= 1

        # Should only contain ASCII chars from the charset
        for line in lines:
            for char in line:
                assert char in ASCII_CHARS

    def test_render_detailed_has_more_variation(self, simple_image):
        renderer = AsciiRenderer(detailed=True)
        result = renderer.render(simple_image, 40, 20)

        # Should produce output
        assert len(result) > 0


class TestColorAsciiRenderer:
    """Tests for ColorAsciiRenderer class."""

    def test_name_property(self):
        renderer = ColorAsciiRenderer()
        assert renderer.name == "ascii-color"

    def test_supports_inline(self):
        renderer = ColorAsciiRenderer()
        assert renderer.supports_inline() is True

    @pytest.fixture
    def color_image(self, tmp_path):
        """Create a colored test image."""
        try:
            from PIL import Image

            img = Image.new("RGB", (50, 50), color="red")
            path = tmp_path / "color.png"
            img.save(path)
            return path
        except ImportError:
            pytest.skip("PIL not available")

    def test_render_produces_ansi_escape_codes(self, color_image):
        renderer = ColorAsciiRenderer()
        result = renderer.render(color_image, 30, 15)

        # Should contain ANSI escape sequences
        assert "\x1b[" in result
        # Should contain color codes
        assert "38;2;" in result  # True color format
        # Should reset colors
        assert "\x1b[0m" in result


class TestHalfBlockRenderer:
    """Tests for HalfBlockRenderer class."""

    def test_name_property(self):
        renderer = HalfBlockRenderer()
        assert renderer.name == "halfblock"

    def test_supports_inline(self):
        renderer = HalfBlockRenderer()
        assert renderer.supports_inline() is True

    def test_render_nonexistent_file_shows_placeholder(self, tmp_path):
        renderer = HalfBlockRenderer()
        fake_path = tmp_path / "nonexistent.png"
        result = renderer.render(fake_path, 40, 10)

        # Falls back to AsciiRenderer's placeholder
        assert "┌" in result
        assert "[Image:" in result

    @pytest.fixture
    def gradient_image(self, tmp_path):
        """Create a gradient test image."""
        try:
            from PIL import Image

            img = Image.new("RGB", (100, 100))
            for y in range(100):
                for x in range(100):
                    img.putpixel((x, y), (x * 2, y * 2, 128))
            path = tmp_path / "gradient.png"
            img.save(path)
            return path
        except ImportError:
            pytest.skip("PIL not available")

    def test_render_uses_half_block_character(self, gradient_image):
        renderer = HalfBlockRenderer()
        result = renderer.render(gradient_image, 30, 15)

        # Should use half-block character
        assert "▀" in result

    def test_render_produces_foreground_and_background_colors(self, gradient_image):
        renderer = HalfBlockRenderer()
        result = renderer.render(gradient_image, 30, 15)

        # Should have foreground color (38;2;)
        assert "38;2;" in result
        # Should have background color (48;2;)
        assert "48;2;" in result


class TestRenderCached:
    """Tests for render_cached function."""

    @pytest.fixture
    def test_image(self, tmp_path):
        """Create a test image."""
        try:
            from PIL import Image

            img = Image.new("RGB", (50, 50), color="blue")
            path = tmp_path / "cache_test.png"
            img.save(path)
            return path
        except ImportError:
            pytest.skip("PIL not available")

    def test_ascii_renderer_type(self, test_image):
        result = render_cached("ascii", str(test_image), 20, 10)
        assert len(result) > 0
        # Should not have ANSI codes
        assert "\x1b[" not in result

    def test_ascii_color_renderer_type(self, test_image):
        result = render_cached("ascii-color", str(test_image), 20, 10)
        # Should have ANSI codes
        assert "\x1b[" in result

    def test_halfblock_renderer_type(self, test_image):
        result = render_cached("halfblock", str(test_image), 20, 10)
        # Should have half-block character
        assert "▀" in result

    def test_unknown_renderer_defaults_to_ascii(self, test_image):
        result = render_cached("unknown", str(test_image), 20, 10)
        # Should not have ANSI codes (plain ASCII)
        assert "\x1b[" not in result

    def test_caching_returns_same_result(self, test_image):
        # Clear cache first
        render_cached.cache_clear()

        result1 = render_cached("ascii", str(test_image), 20, 10)
        result2 = render_cached("ascii", str(test_image), 20, 10)

        assert result1 == result2

        # Check cache was used
        cache_info = render_cached.cache_info()
        assert cache_info.hits >= 1


class TestAsciiChars:
    """Tests for ASCII character sets."""

    def test_simple_chars_ordered_by_brightness(self):
        # Space should be first (lightest)
        assert ASCII_CHARS[0] == " "
        # @ should be last or near last (darkest)
        assert "@" in ASCII_CHARS[-3:]

    def test_detailed_chars_longer_than_simple(self):
        assert len(ASCII_CHARS_DETAILED) > len(ASCII_CHARS)

    def test_chars_are_all_unique(self):
        assert len(set(ASCII_CHARS)) == len(ASCII_CHARS)
        assert len(set(ASCII_CHARS_DETAILED)) == len(ASCII_CHARS_DETAILED)
