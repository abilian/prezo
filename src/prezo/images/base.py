"""Base image renderer protocol and factory."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from prezo.config import get_config
from prezo.terminal import ImageCapability, detect_image_capability

if TYPE_CHECKING:
    from pathlib import Path


class ImageRenderer(Protocol):
    """Protocol for image renderers."""

    def render(self, path: Path, width: int, height: int) -> str:
        """Render an image to a string representation.

        Args:
            path: Path to the image file.
            width: Target width in characters.
            height: Target height in lines.

        Returns:
            String representation of the image for terminal display.

        """
        ...

    def supports_inline(self) -> bool:
        """Check if renderer supports inline display with text.

        Returns:
            True if images can be displayed inline.

        """
        ...

    @property
    def name(self) -> str:
        """Get the renderer name."""
        ...


class NullRenderer:
    """Null renderer that produces no output."""

    @property
    def name(self) -> str:
        """Get the renderer name."""
        return "none"

    def render(self, path: Path, width: int, height: int) -> str:
        """Return empty string (no rendering)."""
        return ""

    def supports_inline(self) -> bool:
        """Null renderer doesn't support inline."""
        return False


def get_renderer(mode: str | None = None) -> ImageRenderer:
    """Get an image renderer based on mode or auto-detection.

    Args:
        mode: Explicit mode ('auto', 'kitty', 'sixel', 'iterm', 'ascii', 'none').
              If None, uses config setting.

    Returns:
        An image renderer instance.

    """
    if mode is None:
        mode = get_config().images.mode

    if mode == "none":
        return NullRenderer()

    if mode == "auto":
        capability = detect_image_capability()
    else:
        # Map mode string to capability
        mode_map = {
            "kitty": ImageCapability.KITTY,
            "sixel": ImageCapability.SIXEL,
            "iterm": ImageCapability.ITERM,
            "ascii": ImageCapability.ASCII,
        }
        capability = mode_map.get(mode, ImageCapability.ASCII)

    # Return appropriate renderer
    if capability == ImageCapability.KITTY:
        from .kitty import KittyRenderer

        return KittyRenderer()

    if capability == ImageCapability.ITERM:
        from .iterm import ItermRenderer

        return ItermRenderer()

    if capability == ImageCapability.SIXEL:
        from .sixel import SixelRenderer

        return SixelRenderer()

    # Default to ASCII
    from .ascii import AsciiRenderer

    return AsciiRenderer()
