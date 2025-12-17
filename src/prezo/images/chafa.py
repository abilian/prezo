"""Chafa-based image renderer for high-quality terminal graphics."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def chafa_available() -> bool:
    """Check if chafa is installed."""
    return shutil.which("chafa") is not None


def render_with_chafa(
    path: Path,
    width: int,
    height: int,
    *,
    symbols: str = "block+border+space",
    colors: str = "full",
) -> str | None:
    """Render an image using chafa.

    Args:
        path: Path to the image file.
        width: Target width in characters.
        height: Target height in lines.
        symbols: Symbol set to use (block, border, space, ascii, etc.).
        colors: Color mode (full, 256, 16, 8, 2, none).

    Returns:
        Rendered image as ANSI string, or None if chafa not available.

    """
    if not chafa_available():
        return None

    if not path.exists():
        return None

    chafa_path = shutil.which("chafa")
    if not chafa_path:
        return None

    try:
        result = subprocess.run(
            [
                chafa_path,
                "--size",
                f"{width}x{height}",
                "--format",
                "symbols",  # Force symbols, not native protocols
                "--symbols",
                symbols,
                "--colors",
                colors,
                "--color-space",
                "rgb",
                "--dither",
                "ordered",
                "--work",
                "9",  # Maximum quality
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass

    return None


class ChafaRenderer:
    """Render images using chafa for high-quality terminal graphics."""

    def __init__(self) -> None:
        """Initialize the chafa renderer."""
        self._available = chafa_available()

    @property
    def name(self) -> str:
        """Get the renderer name."""
        return "chafa"

    @property
    def available(self) -> bool:
        """Check if chafa is available."""
        return self._available

    def supports_inline(self) -> bool:
        """Chafa supports inline display."""
        return True

    def render(self, path: Path, width: int, height: int) -> str:
        """Render an image using chafa.

        Args:
            path: Path to the image file.
            width: Target width in characters.
            height: Target height in lines.

        Returns:
            Rendered image as ANSI string.

        """
        result = render_with_chafa(path, width, height)
        if result:
            return result

        # Fall back to placeholder if chafa fails
        return self._render_placeholder(path, width, height)

    def _render_placeholder(self, path: Path, width: int, height: int) -> str:
        """Render a placeholder when image can't be loaded."""
        name = (
            path.name if len(path.name) < width - 4 else path.name[: width - 7] + "..."
        )
        box_width = max(len(name) + 4, 20)
        box_width = min(box_width, width)

        lines = []
        lines.append("┌" + "─" * (box_width - 2) + "┐")
        lines.append("│" + " " * (box_width - 2) + "│")
        lines.append("│" + f"[Image: {name}]".center(box_width - 2) + "│")
        lines.append("│" + " " * (box_width - 2) + "│")
        lines.append("└" + "─" * (box_width - 2) + "┘")

        return "\n".join(lines)
