"""Sixel graphics image renderer."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class SixelRenderer:
    """Render images using Sixel graphics."""

    @property
    def name(self) -> str:
        """Get the renderer name."""
        return "sixel"

    def supports_inline(self) -> bool:
        """Sixel supports inline images."""
        return True

    def render(self, path: Path, width: int, height: int) -> str:
        """Render an image using Sixel graphics.

        Args:
            path: Path to the image file.
            width: Target width in characters.
            height: Target height in lines.

        Returns:
            Sixel escape sequence string to display the image.

        """
        try:
            return self._render_with_libsixel(path, width, height)
        except ImportError:
            # libsixel not available, try PIL-based fallback
            try:
                return self._render_with_pil(path, width, height)
            except Exception:
                from .ascii import AsciiRenderer

                return AsciiRenderer()._render_placeholder(path, width, height)
        except Exception:
            from .ascii import AsciiRenderer

            return AsciiRenderer()._render_placeholder(path, width, height)

    def _render_with_libsixel(self, path: Path, width: int, height: int) -> str:
        """Render using libsixel-python."""
        import libsixel
        from PIL import Image

        # Load and resize image
        img: Image.Image = Image.open(path)
        img = img.convert("RGB")

        # Calculate pixel dimensions
        # Assume ~10 pixels per character width, ~20 per height
        pixel_width = width * 10
        pixel_height = height * 20

        # Maintain aspect ratio
        aspect = img.width / img.height
        if pixel_width / pixel_height > aspect:
            pixel_width = int(pixel_height * aspect)
        else:
            pixel_height = int(pixel_width / aspect)

        img = img.resize((pixel_width, pixel_height))

        # Convert to sixel
        output = libsixel.encoder()
        output.setopt(libsixel.SIXEL_OPTFLAG_WIDTH, str(pixel_width))
        output.setopt(libsixel.SIXEL_OPTFLAG_HEIGHT, str(pixel_height))

        # Encode to sixel string
        # This is a simplified approach - actual libsixel usage may vary
        data = img.tobytes()
        return output.encode(data, pixel_width, pixel_height)

    def _render_with_pil(self, path: Path, width: int, height: int) -> str:
        """Render using pure PIL (simplified sixel encoder).

        This is a basic sixel encoder for terminals that support sixel
        but when libsixel is not available.

        """
        from PIL import Image

        img: Image.Image = Image.open(path)
        img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)

        # Calculate pixel dimensions
        pixel_width = width * 8
        pixel_height = height * 16

        # Maintain aspect ratio
        aspect = img.width / img.height
        if pixel_width / pixel_height > aspect:
            pixel_width = int(pixel_height * aspect)
        else:
            pixel_height = int(pixel_width / aspect)

        # Make height divisible by 6 (sixel row height)
        pixel_height = (pixel_height // 6) * 6

        img = img.resize((pixel_width, pixel_height))

        # Get palette
        palette = img.getpalette()
        pixels = list(img.getdata())

        # Build sixel output
        output = []

        # Start sixel sequence
        output.append("\x1bPq")

        # Define colors from palette
        if palette:
            for i in range(256):
                r = palette[i * 3]
                g = palette[i * 3 + 1]
                b = palette[i * 3 + 2]
                # Convert to percentages
                r_pct = int(r / 255 * 100)
                g_pct = int(g / 255 * 100)
                b_pct = int(b / 255 * 100)
                output.append(f"#{i};2;{r_pct};{g_pct};{b_pct}")

        # Encode pixels in sixel format
        # Each sixel row is 6 pixels high
        for row in range(0, pixel_height, 6):
            # For each color used in this row
            colors_in_row: dict[int, list[int]] = {}

            for y in range(6):
                if row + y >= pixel_height:
                    break
                for x in range(pixel_width):
                    pixel_idx = (row + y) * pixel_width + x
                    if pixel_idx < len(pixels):
                        color = pixels[pixel_idx]
                        if color not in colors_in_row:
                            colors_in_row[color] = [0] * pixel_width
                        colors_in_row[color][x] |= 1 << y

            # Output each color's sixels for this row
            for color, sixels in colors_in_row.items():
                output.append(f"#{color}")
                output.extend(chr(s + 63) for s in sixels)
                output.append("$")  # Carriage return

            output.append("-")  # New line

        # End sixel sequence
        output.append("\x1b\\")

        return "".join(output)


def is_sixel_available() -> bool:
    """Check if sixel rendering is available."""
    try:
        import libsixel  # noqa: F401

        return True
    except ImportError:
        pass

    try:
        from PIL import Image  # noqa: F401

        return True
    except ImportError:
        pass

    return False
