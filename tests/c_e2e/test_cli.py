"""Tests for CLI functionality and error handling."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def get_prezo_command():
    """Get the prezo command path."""
    cmd = shutil.which("prezo")
    if cmd:
        return [cmd]
    # Fall back to running via uv
    uv = shutil.which("uv")
    if uv:
        return [uv, "run", "prezo"]
    pytest.skip("prezo command not found")


class TestCLIErrorHandling:
    """Tests for CLI error handling."""

    def test_missing_file_shows_friendly_error(self, tmp_path: Path):
        """Test that missing file shows friendly error message."""
        cmd = get_prezo_command()
        result = subprocess.run(
            [*cmd, str(tmp_path / "nonexistent.md")],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "error:" in result.stderr
        assert "file not found" in result.stderr
        assert "Make sure the file exists" in result.stderr

    def test_export_missing_file_shows_error(self, tmp_path: Path):
        """Test that export with missing file shows error."""
        cmd = get_prezo_command()
        result = subprocess.run(
            [*cmd, "-e", "png", str(tmp_path / "missing.md")],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "error:" in result.stderr

    def test_export_without_file_shows_error(self):
        """Test that export without file argument shows error."""
        cmd = get_prezo_command()
        result = subprocess.run(
            [*cmd, "-e", "png"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "error:" in result.stderr
        assert "requires a presentation file" in result.stderr

    def test_directory_instead_of_file_shows_error(self, tmp_path: Path):
        """Test that providing a directory shows friendly error."""
        cmd = get_prezo_command()
        result = subprocess.run(
            [*cmd, str(tmp_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "error:" in result.stderr
        assert "expected a file, got a directory" in result.stderr

    def test_non_md_file_shows_warning(self, tmp_path: Path):
        """Test that non-.md file shows warning but continues."""
        # Create a file with wrong extension
        test_file = tmp_path / "presentation.txt"
        test_file.write_text("# Slide 1")

        cmd = get_prezo_command()
        result = subprocess.run(
            [*cmd, "-e", "svg", str(test_file)],
            check=False,
            capture_output=True,
            text=True,
        )
        # Should show warning but still export
        assert "warning:" in result.stderr
        assert "does not have a .md extension" in result.stderr


class TestPNGSVGExportCLI:
    """Tests for PNG/SVG export via CLI."""

    def test_png_export_all_slides(self, tmp_path: Path):
        """Test exporting all slides to PNG via CLI."""
        source = tmp_path / "presentation.md"
        source.write_text("# Slide 1\n\n---\n\n# Slide 2")
        output_dir = tmp_path / "output"

        cmd = get_prezo_command()
        result = subprocess.run(
            [*cmd, "-e", "png", str(source), "-o", str(output_dir)],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Exported" in result.stdout or "Exported" in result.stderr

    def test_svg_export_single_slide(self, tmp_path: Path):
        """Test exporting single slide to SVG via CLI."""
        source = tmp_path / "presentation.md"
        source.write_text("# Slide 1\n\n---\n\n# Slide 2\n\n---\n\n# Slide 3")
        output = tmp_path / "slide.svg"

        cmd = get_prezo_command()
        result = subprocess.run(
            [*cmd, "-e", "svg", str(source), "--slide", "2", "-o", str(output)],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert output.exists()

    def test_invalid_slide_number_shows_error(self, tmp_path: Path):
        """Test that invalid slide number shows error."""
        source = tmp_path / "presentation.md"
        source.write_text("# Slide 1")

        cmd = get_prezo_command()
        result = subprocess.run(
            [*cmd, "-e", "svg", str(source), "--slide", "99"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "Invalid slide number" in result.stderr


class TestValidateFile:
    """Tests for _validate_file function."""

    def test_validate_existing_md_file(self, tmp_path: Path):
        """Test validation of existing .md file."""
        from prezo import _validate_file

        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        result = _validate_file(test_file)
        assert result == test_file.resolve()

    def test_validate_markdown_extension(self, tmp_path: Path):
        """Test validation of .markdown extension."""
        from prezo import _validate_file

        test_file = tmp_path / "test.markdown"
        test_file.write_text("# Test")

        result = _validate_file(test_file)
        assert result == test_file.resolve()

    def test_validate_resolves_path(self, tmp_path: Path):
        """Test that _validate_file resolves relative paths."""
        from prezo import _validate_file

        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        result = _validate_file(test_file)
        assert result.is_absolute()
