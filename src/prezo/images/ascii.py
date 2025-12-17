"""ASCII art image renderer."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# ASCII characters from dark to light
ASCII_CHARS = " .:-=+*#%@"
ASCII_CHARS_DETAILED = (
    " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
)


class AsciiRenderer:
    """Render images as ASCII art."""

    def __init__(self, detailed: bool = False) -> None:
        """Initialize ASCII renderer.

        Args:
            detailed: Use detailed character set for more gradients.

        """
        self.chars = ASCII_CHARS_DETAILED if detailed else ASCII_CHARS

    @property
    def name(self) -> str:
        """Get the renderer name."""
        return "ascii"

    def supports_inline(self) -> bool:
        """ASCII art supports inline display."""
        return True

    def render(self, path: Path, width: int, height: int) -> str:
        """Render an image as ASCII art.

        Args:
            path: Path to the image file.
            width: Target width in characters.
            height: Target height in lines.

        Returns:
            ASCII art string representation.

        """
        try:
            return self._render_image(path, width, height)
        except Exception:
            return self._render_placeholder(path, width, height)

    def _render_image(self, path: Path, width: int, height: int) -> str:
        """Render image using PIL."""
        from PIL import Image

        img = Image.open(path)

        # Convert to grayscale
        img = img.convert("L")

        # Calculate aspect ratio correction
        # Terminal characters are typically ~2x taller than wide
        aspect_ratio = img.width / img.height
        new_width = min(width, int(height * 2 * aspect_ratio))
        new_height = min(height, int(new_width / aspect_ratio / 2))

        # Resize
        img = img.resize((new_width, new_height))

        # Convert to ASCII
        pixels = list(img.getdata())
        lines = []

        for y in range(new_height):
            line = ""
            for x in range(new_width):
                pixel = pixels[y * new_width + x]
                # Map pixel value (0-255) to character
                char_idx = int(pixel / 256 * len(self.chars))
                char_idx = min(char_idx, len(self.chars) - 1)
                line += self.chars[char_idx]
            lines.append(line)

        return "\n".join(lines)

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


class ColorAsciiRenderer(AsciiRenderer):
    """Render images as colored ASCII art using ANSI colors."""

    @property
    def name(self) -> str:
        """Get the renderer name."""
        return "ascii-color"

    def _render_image(self, path: Path, width: int, height: int) -> str:
        """Render image as colored ASCII."""
        from PIL import Image

        img = Image.open(path)

        # Keep color, convert to RGB
        img = img.convert("RGB")

        # Calculate aspect ratio correction
        aspect_ratio = img.width / img.height
        new_width = min(width, int(height * 2 * aspect_ratio))
        new_height = min(height, int(new_width / aspect_ratio / 2))

        # Resize
        img = img.resize((new_width, new_height))

        # Convert to colored ASCII
        pixels = list(img.getdata())
        lines = []

        for y in range(new_height):
            line = ""
            for x in range(new_width):
                r, g, b = pixels[y * new_width + x]
                # Use half-block character with true color
                line += f"\x1b[38;2;{r};{g};{b}m█\x1b[0m"
            lines.append(line)

        return "\n".join(lines)


class HalfBlockRenderer:
    """Render images using Unicode half-block characters for higher resolution."""

    @property
    def name(self) -> str:
        """Get the renderer name."""
        return "halfblock"

    def supports_inline(self) -> bool:
        """Half-block supports inline display."""
        return True

    def render(self, path: Path, width: int, height: int) -> str:
        """Render image using half-block characters.

        Each character cell displays 2 vertical pixels using the upper
        half block character (▀) with foreground and background colors.

        Args:
            path: Path to the image file.
            width: Target width in characters.
            height: Target height in lines.

        Returns:
            Colored half-block string representation.

        """
        try:
            return self._render_image(path, width, height)
        except Exception:
            return AsciiRenderer()._render_placeholder(path, width, height)

    def _render_image(self, path: Path, width: int, height: int) -> str:
        """Render image using half-blocks."""
        from PIL import Image

        img = Image.open(path)
        img = img.convert("RGB")

        # Calculate dimensions (height is doubled because of half-blocks)
        aspect_ratio = img.width / img.height
        new_width = min(width, int(height * 2 * aspect_ratio))
        # Height in pixels (2 pixels per character row)
        new_height = min(height * 2, int(new_width / aspect_ratio))
        # Make height even
        new_height = new_height - (new_height % 2)

        img = img.resize((new_width, new_height))
        pixels = list(img.getdata())

        lines = []
        for y in range(0, new_height, 2):
            line = ""
            for x in range(new_width):
                # Upper pixel
                r1, g1, b1 = pixels[y * new_width + x]
                # Lower pixel (or black if at edge)
                if y + 1 < new_height:
                    r2, g2, b2 = pixels[(y + 1) * new_width + x]
                else:
                    r2, g2, b2 = 0, 0, 0

                # Upper half block: foreground = top, background = bottom
                line += f"\x1b[38;2;{r1};{g1};{b1};48;2;{r2};{g2};{b2}m▀\x1b[0m"
            lines.append(line)

        return "\n".join(lines)


@lru_cache(maxsize=32)
def render_cached(
    renderer_name: str,
    path: str,
    width: int,
    height: int,
) -> str:
    """Render an image with caching.

    Args:
        renderer_name: Name of the renderer to use.
        path: Path to the image file.
        width: Target width.
        height: Target height.

    Returns:
        Rendered image string.

    """
    renderers = {
        "ascii": AsciiRenderer,
        "ascii-color": ColorAsciiRenderer,
        "halfblock": HalfBlockRenderer,
    }
    renderer_cls = renderers.get(renderer_name, AsciiRenderer)
    renderer = renderer_cls()
    return renderer.render(Path(path), width, height)
