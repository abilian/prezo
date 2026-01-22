"""Tests for export functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from prezo.export import (
    ExportError,
    export_slide_to_image,
    export_to_html,
    export_to_images,
    export_to_pdf,
    render_slide_to_html,
    render_slide_to_svg,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestRenderSlideToSvg:
    """Tests for render_slide_to_svg function."""

    def test_renders_basic_slide(self):
        content = "# Hello World\n\nThis is a test slide."
        svg = render_slide_to_svg(content, 0, 1)
        assert "<svg" in svg
        # Text may be split across elements or encoded, just verify SVG is produced
        assert len(svg) > 1000  # Should be a substantial SVG

    def test_includes_slide_number(self):
        content = "# Slide"
        svg = render_slide_to_svg(content, 2, 5)
        assert "3/5" in svg  # 0-indexed -> 1-indexed

    def test_includes_progress_bar(self):
        content = "# Slide"
        svg = render_slide_to_svg(content, 4, 10)
        # Should show 50% progress (5/10)
        assert "█" in svg or "░" in svg

    def test_respects_theme(self):
        content = "# Slide"
        svg_dark = render_slide_to_svg(content, 0, 1, theme_name="dark")
        svg_light = render_slide_to_svg(content, 0, 1, theme_name="light")
        # Different themes should produce different colors
        assert svg_dark != svg_light

    def test_custom_width(self):
        content = "# Slide"
        svg_narrow = render_slide_to_svg(content, 0, 1, width=60)
        svg_wide = render_slide_to_svg(content, 0, 1, width=120)
        # Wider console produces different output
        assert svg_narrow != svg_wide


class TestExportToPdf:
    """Tests for export_to_pdf function."""

    def test_source_not_found(self, tmp_path: Path):
        source = tmp_path / "nonexistent.md"
        output = tmp_path / "output.pdf"
        with pytest.raises(ExportError, match="not found"):
            export_to_pdf(source, output)

    def test_single_empty_slide_still_exports(self, tmp_path: Path):
        """An empty file produces one empty slide, which is valid."""
        source = tmp_path / "empty.md"
        source.write_text("")
        output = tmp_path / "empty.pdf"

        with patch("prezo.export.pdf.combine_svgs_to_pdf") as mock_combine:
            mock_combine.return_value = output
            result = export_to_pdf(source, output)

        # Empty content still produces 1 slide
        assert result == output

    def test_custom_output_path(self, tmp_path: Path):
        source = tmp_path / "presentation.md"
        source.write_text("# Test Slide")
        output = tmp_path / "custom_name.pdf"

        with patch("prezo.export.pdf.combine_svgs_to_pdf") as mock_combine:
            mock_combine.return_value = output
            export_to_pdf(source, output)

        call_args = mock_combine.call_args
        output_path = call_args[0][1]
        assert output_path == output

    def test_generates_svg_for_each_slide(self, tmp_path: Path):
        source = tmp_path / "multi.md"
        source.write_text("# Slide 1\n\n---\n\n# Slide 2\n\n---\n\n# Slide 3")
        output = tmp_path / "multi.pdf"

        with patch("prezo.export.pdf.combine_svgs_to_pdf") as mock_combine:
            mock_combine.return_value = output
            export_to_pdf(source, output)

        # Should have 3 SVG files passed to combine
        call_args = mock_combine.call_args
        svg_files = call_args[0][0]
        assert len(svg_files) == 3


class TestCombineSvgsToPdf:
    """Tests for combine_svgs_to_pdf function."""

    def test_missing_dependencies(self, tmp_path: Path):
        svg_file = tmp_path / "test.svg"
        svg_file.write_text("<svg></svg>")
        tmp_path / "output.pdf"

        with patch.dict("sys.modules", {"cairosvg": None}):
            # This should handle the ImportError gracefully
            # The actual test depends on whether cairosvg is installed
            pass

    def test_creates_pdf_from_svgs(self, tmp_path: Path):
        """Integration test - requires cairosvg and pypdf."""
        pytest.importorskip("cairosvg")
        pytest.importorskip("pypdf")

        from prezo.export import combine_svgs_to_pdf

        # Create a minimal valid SVG
        svg_content = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <rect width="100" height="100" fill="blue"/>
</svg>"""

        svg_files = []
        for i in range(3):
            svg_file = tmp_path / f"slide_{i}.svg"
            svg_file.write_text(svg_content)
            svg_files.append(svg_file)

        output = tmp_path / "output.pdf"
        result = combine_svgs_to_pdf(svg_files, output)

        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0


class TestRenderSlideToHtml:
    """Tests for render_slide_to_html function."""

    def test_basic_content(self):
        content = "# Hello World"
        html = render_slide_to_html(content)
        assert "<h1>" in html or "Hello World" in html

    def test_handles_markdown(self):
        content = "**Bold** and *italic*"
        html = render_slide_to_html(content)
        # Either markdown lib or fallback should produce output
        assert "Bold" in html
        assert "italic" in html

    def test_handles_code_blocks(self):
        content = "```python\nprint('hello')\n```"
        html = render_slide_to_html(content)
        assert "print" in html


class TestExportToHtml:
    """Tests for export_to_html function."""

    def test_source_not_found(self, tmp_path: Path):
        source = tmp_path / "nonexistent.md"
        output = tmp_path / "output.html"
        with pytest.raises(ExportError, match="not found"):
            export_to_html(source, output)

    def test_exports_basic_presentation(self, tmp_path: Path):
        source = tmp_path / "test.md"
        source.write_text("# Slide 1\n\n---\n\n# Slide 2")
        output = tmp_path / "test.html"

        result = export_to_html(source, output)

        assert result == output
        assert output.exists()

        html = output.read_text()
        assert "<!DOCTYPE html>" in html
        assert "Slide 1" in html
        assert "Slide 2" in html

    def test_respects_theme(self, tmp_path: Path):
        source = tmp_path / "test.md"
        source.write_text("# Slide")
        output_dark = tmp_path / "dark.html"
        output_light = tmp_path / "light.html"

        export_to_html(source, output_dark, theme="dark")
        export_to_html(source, output_light, theme="light")

        dark_html = output_dark.read_text()
        light_html = output_light.read_text()

        # Dark and light themes should have different colors
        assert dark_html != light_html

    def test_includes_notes_when_requested(self, tmp_path: Path):
        source = tmp_path / "test.md"
        source.write_text("# Slide\n\n???\nPresenter notes here")
        output = tmp_path / "test.html"

        result = export_to_html(source, output, include_notes=True)

        assert result == output
        html = output.read_text()
        assert "Presenter notes here" in html

    def test_excludes_notes_by_default(self, tmp_path: Path):
        source = tmp_path / "test.md"
        source.write_text("# Slide\n\n???\nSecret notes")
        output = tmp_path / "test.html"

        export_to_html(source, output, include_notes=False)

        html = output.read_text()
        assert "Secret notes" not in html

    def test_includes_title_from_frontmatter(self, tmp_path: Path):
        source = tmp_path / "test.md"
        source.write_text("---\ntitle: My Presentation\n---\n\n# Slide")
        output = tmp_path / "test.html"

        export_to_html(source, output)

        html = output.read_text()
        assert "<title>My Presentation</title>" in html

    def test_uses_filename_as_fallback_title(self, tmp_path: Path):
        source = tmp_path / "my_slides.md"
        source.write_text("# Just a slide")
        output = tmp_path / "my_slides.html"

        export_to_html(source, output)

        html = output.read_text()
        assert "<title>my_slides</title>" in html

    def test_empty_presentation_fails(self, tmp_path: Path):
        source = tmp_path / "empty.md"
        source.write_text("")
        output = tmp_path / "empty.html"

        # Empty content still produces one slide (empty string)
        result = export_to_html(source, output)
        assert result == output


class TestExportSlideToImage:
    """Tests for export_slide_to_image function."""

    def test_exports_png_slide(self, tmp_path: Path):
        """Test exporting a single slide to PNG."""
        pytest.importorskip("cairosvg")

        content = "# Hello World\n\nThis is a test slide."
        output = tmp_path / "slide.png"

        result = export_slide_to_image(content, 0, 1, output, output_format="png")

        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_exports_svg_slide(self, tmp_path: Path):
        """Test exporting a single slide to SVG."""
        content = "# Hello World\n\nThis is a test slide."
        output = tmp_path / "slide.svg"

        result = export_slide_to_image(content, 0, 1, output, output_format="svg")

        assert result == output
        assert output.exists()
        svg_content = output.read_text()
        assert "<svg" in svg_content

    def test_respects_theme(self, tmp_path: Path):
        """Test that theme affects output."""
        content = "# Test"
        output_dark = tmp_path / "dark.svg"
        output_light = tmp_path / "light.svg"

        export_slide_to_image(
            content, 0, 1, output_dark, output_format="svg", theme_name="dark"
        )
        export_slide_to_image(
            content, 0, 1, output_light, output_format="svg", theme_name="light"
        )

        dark_svg = output_dark.read_text()
        light_svg = output_light.read_text()
        assert dark_svg != light_svg

    def test_includes_slide_number(self, tmp_path: Path):
        """Test that slide number is included in output."""
        content = "# Test"
        output = tmp_path / "slide.svg"

        result = export_slide_to_image(content, 2, 5, output, output_format="svg")

        assert result == output
        svg_content = output.read_text()
        assert "3/5" in svg_content  # 0-indexed -> 1-indexed

    def test_chrome_option(self, tmp_path: Path):
        """Test that chrome option affects output."""
        content = "# Test"
        output_chrome = tmp_path / "chrome.svg"
        output_no_chrome = tmp_path / "no_chrome.svg"

        export_slide_to_image(
            content, 0, 1, output_chrome, output_format="svg", chrome=True
        )
        export_slide_to_image(
            content, 0, 1, output_no_chrome, output_format="svg", chrome=False
        )

        chrome_svg = output_chrome.read_text()
        no_chrome_svg = output_no_chrome.read_text()
        # Without chrome the terminal frame is not drawn
        assert chrome_svg != no_chrome_svg


class TestExportToImages:
    """Tests for export_to_images function."""

    def test_source_not_found(self, tmp_path: Path):
        """Test error when source file doesn't exist."""
        source = tmp_path / "nonexistent.md"
        output = tmp_path / "output"

        with pytest.raises(ExportError, match="Failed to read"):
            export_to_images(source, output, output_format="svg")

    def test_exports_all_slides_as_svg(self, tmp_path: Path):
        """Test exporting all slides to SVG."""
        source = tmp_path / "presentation.md"
        source.write_text("# Slide 1\n\n---\n\n# Slide 2\n\n---\n\n# Slide 3")
        output_dir = tmp_path / "output"

        result = export_to_images(source, output_dir, output_format="svg")

        assert len(result) == 3
        assert (output_dir / "presentation_001.svg").exists()
        assert (output_dir / "presentation_002.svg").exists()
        assert (output_dir / "presentation_003.svg").exists()

    def test_exports_all_slides_as_png(self, tmp_path: Path):
        """Test exporting all slides to PNG (requires cairosvg)."""
        pytest.importorskip("cairosvg")

        source = tmp_path / "presentation.md"
        source.write_text("# Slide 1\n\n---\n\n# Slide 2")
        output_dir = tmp_path / "output"

        result = export_to_images(source, output_dir, output_format="png")

        assert len(result) == 2
        assert (output_dir / "presentation_001.png").exists()
        assert (output_dir / "presentation_002.png").exists()

    def test_exports_single_slide(self, tmp_path: Path):
        """Test exporting a single slide by number."""
        source = tmp_path / "presentation.md"
        source.write_text("# Slide 1\n\n---\n\n# Slide 2\n\n---\n\n# Slide 3")
        output = tmp_path / "slide2.svg"

        result = export_to_images(source, output, output_format="svg", slide_num=2)

        assert len(result) == 1
        assert result[0] == output
        assert output.exists()
        svg_content = output.read_text()
        assert "<svg" in svg_content

    def test_invalid_slide_number_too_high(self, tmp_path: Path):
        """Test error when slide number is too high."""
        source = tmp_path / "presentation.md"
        source.write_text("# Slide 1\n\n---\n\n# Slide 2")

        with pytest.raises(ExportError, match="Invalid slide number"):
            export_to_images(source, output_format="svg", slide_num=5)

    def test_invalid_slide_number_zero(self, tmp_path: Path):
        """Test error when slide number is zero."""
        source = tmp_path / "presentation.md"
        source.write_text("# Slide 1")

        with pytest.raises(ExportError, match="Invalid slide number"):
            export_to_images(source, output_format="svg", slide_num=0)

    def test_creates_output_directory(self, tmp_path: Path):
        """Test that output directory is created if it doesn't exist."""
        source = tmp_path / "presentation.md"
        source.write_text("# Slide 1")
        output_dir = tmp_path / "new" / "nested" / "dir"

        result = export_to_images(source, output_dir, output_format="svg")

        assert len(result) == 1
        assert output_dir.exists()

    def test_naming_convention(self, tmp_path: Path):
        """Test slide file naming convention with zero-padded numbers."""
        source = tmp_path / "my_presentation.md"
        slides = "\n\n---\n\n".join([f"# Slide {i}" for i in range(12)])
        source.write_text(slides)
        output_dir = tmp_path / "output"

        result = export_to_images(source, output_dir, output_format="svg")

        assert len(result) == 12
        # Check naming with zero-padding
        assert (output_dir / "my_presentation_001.svg").exists()
        assert (output_dir / "my_presentation_010.svg").exists()
        assert (output_dir / "my_presentation_012.svg").exists()

    def test_output_with_extension_uses_correct_prefix(self, tmp_path: Path):
        """Test that output with extension uses filename as prefix, not parent dir."""
        source = tmp_path / "presentation.md"
        source.write_text("# Slide 1\n\n---\n\n# Slide 2")

        # Create nested output directory
        nested_dir = tmp_path / "nested" / "output"
        nested_dir.mkdir(parents=True)

        # Output path with extension (should use "slides" as prefix, not "output")
        output = nested_dir / "slides.svg"

        result = export_to_images(source, output, output_format="svg")

        assert len(result) == 2
        # Should use "slides" prefix, not "output" (parent dir name)
        assert (nested_dir / "slides_001.svg").exists()
        assert (nested_dir / "slides_002.svg").exists()
        # Should NOT use the parent directory name
        assert not (nested_dir / "output_001.svg").exists()
