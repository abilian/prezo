"""iTerm2 image renderer using inline images protocol."""

from __future__ import annotations

import base64
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class ItermRenderer:
    """Render images using iTerm2's inline images protocol."""

    @property
    def name(self) -> str:
        """Get the renderer name."""
        return "iterm"

    def supports_inline(self) -> bool:
        """iTerm2 supports inline images."""
        return True

    def render(self, path: Path, width: int, height: int) -> str:
        """Render an image using iTerm2 inline images protocol.

        Args:
            path: Path to the image file.
            width: Target width in characters.
            height: Target height in lines.

        Returns:
            Escape sequence string to display the image.

        """
        try:
            return self._render_image(path, width, height)
        except Exception:
            from .ascii import AsciiRenderer

            return AsciiRenderer()._render_placeholder(path, width, height)

    def _render_image(self, path: Path, width: int, height: int) -> str:
        """Render image using iTerm2 protocol."""
        # Read and encode image
        image_data = path.read_bytes()
        encoded = base64.b64encode(image_data).decode("ascii")

        # Get file name for the name parameter
        name = base64.b64encode(path.name.encode()).decode("ascii")

        # Build iTerm2 inline image escape sequence
        # Format: \x1b]1337;File=name=<b64name>;size=<bytes>;width=<w>;height=<h>;inline=1:<b64data>\x07
        #
        # name: base64 encoded filename
        # size: file size in bytes
        # width: width (can be pixels, cells, percent, or auto)
        # height: height (same options)
        # inline: 1 = display inline, 0 = download
        # preserveAspectRatio: 1 = preserve, 0 = stretch

        params = [
            f"name={name}",
            f"size={len(image_data)}",
            f"width={width}",
            f"height={height}",
            "inline=1",
            "preserveAspectRatio=1",
        ]

        param_str = ";".join(params)
        return f"\x1b]1337;File={param_str}:{encoded}\x07"

    def render_with_options(
        self,
        path: Path,
        *,
        width: str = "auto",
        height: str = "auto",
        preserve_aspect: bool = True,
    ) -> str:
        """Render image with more control over sizing.

        Args:
            path: Path to the image file.
            width: Width specification (e.g., "80", "50%", "auto", "80px").
            height: Height specification.
            preserve_aspect: Whether to preserve aspect ratio.

        Returns:
            Escape sequence string.

        """
        image_data = path.read_bytes()
        encoded = base64.b64encode(image_data).decode("ascii")
        name = base64.b64encode(path.name.encode()).decode("ascii")

        params = [
            f"name={name}",
            f"size={len(image_data)}",
            f"width={width}",
            f"height={height}",
            "inline=1",
            f"preserveAspectRatio={1 if preserve_aspect else 0}",
        ]

        param_str = ";".join(params)
        return f"\x1b]1337;File={param_str}:{encoded}\x07"


def write_image_to_terminal(path: Path, width: int = 80, height: int = 24) -> None:
    """Write an image directly to the terminal.

    Utility function for direct terminal output.

    Args:
        path: Path to the image file.
        width: Target width in cells.
        height: Target height in cells.

    """
    renderer = ItermRenderer()
    output = renderer.render(path, width, height)
    sys.stdout.write(output)
    sys.stdout.flush()
