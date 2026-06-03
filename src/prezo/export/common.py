"""Common utilities and constants for export functionality."""

from __future__ import annotations

import base64
import mimetypes
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from prezo.parser import Slide


class ExportError(Exception):
    """Raised when an export operation fails."""


def image_data_uri(image_path: Path) -> str | None:
    """Read an image file and return it as a base64 ``data:`` URI.

    Args:
        image_path: Path to the image file.

    Returns:
        A ``data:<mime>;base64,<data>`` URI, or None if the file is unreadable.

    """
    try:
        data = image_path.read_bytes()
    except OSError:
        return None
    mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def resolve_slide_image(slide: Slide, source: Path | None) -> tuple[Path | None, str]:
    """Resolve a slide's first image to an absolute path for embedding.

    Args:
        slide: The slide whose image to resolve.
        source: Path to the presentation file (for relative resolution).

    Returns:
        Tuple of (resolved path or None, layout directive).

    """
    from prezo.images.processor import resolve_image_path  # noqa: PLC0415

    if not slide.images:
        return None, "fit"
    image = slide.images[0]
    return resolve_image_path(image.path, source), image.layout


# Exit codes for CLI (only used in run_* wrapper functions)
EXIT_SUCCESS = 0
EXIT_FAILURE = 2

# Backwards compatibility aliases (deprecated, use exceptions instead)
EXPORT_SUCCESS = EXIT_SUCCESS
EXPORT_FAILED = EXIT_FAILURE


def check_font_availability() -> list[str]:
    """Check if required fonts are available on the system.

    Returns a list of warning messages (empty if all fonts are available).
    """
    warnings = []

    # Check for fc-list (fontconfig) to query system fonts
    fc_list_path = shutil.which("fc-list")
    if fc_list_path:
        try:
            result = subprocess.run(
                [fc_list_path, ":family"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            fonts = result.stdout.lower()

            # Check for Fira Code (primary monospace font)
            if "fira code" not in fonts and "firacode" not in fonts:
                warnings.append(
                    "Fira Code font not found. Install it for best results:\n"
                    "  macOS: brew install --cask font-fira-code\n"
                    "  Ubuntu: sudo apt install fonts-firacode\n"
                    "  Or download from: https://github.com/tonsky/FiraCode"
                )

        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            # Can't check fonts, skip warning
            pass
    else:
        # No fontconfig available (Windows or minimal system)
        # We can't easily check fonts, so just note the requirement
        warnings.append(
            "Cannot verify font availability. For correct alignment, ensure "
            "Fira Code font is installed."
        )

    return warnings


def print_font_warnings(warnings: list[str]) -> None:
    """Print font warnings to stderr."""
    if warnings:
        print("\n⚠️  Font Warning:", file=sys.stderr)
        for warning in warnings:
            for line in warning.split("\n"):
                print(f"   {line}", file=sys.stderr)
        print(
            "\n   Without proper fonts, column alignment may be incorrect in exports.",
            file=sys.stderr,
        )
        print(file=sys.stderr)
