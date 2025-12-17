"""Image overlay system for native terminal image rendering.

This module provides a way to render images directly to the terminal,
bypassing Textual's virtual buffer. It works by:
1. Having placeholder widgets reserve space in the TUI
2. After Textual renders, writing images directly at specific screen coordinates
3. Using terminal-specific protocols (iTerm2, Kitty, Sixel) for native quality

This approach is similar to how ranger and other TUI tools display images.
"""

from __future__ import annotations

import contextlib
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO

from typing_extensions import Self

from prezo.terminal import ImageCapability, detect_image_capability

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@dataclass
class ImageRequest:
    """Request to render an image at a specific screen position."""

    path: Path
    row: int  # 1-based screen row
    col: int  # 1-based screen column
    width: int  # Width in characters
    height: int  # Height in lines


class ImageOverlayRenderer:
    """Renders images directly to the terminal, bypassing Textual's buffer.

    This is a singleton that manages all image rendering for the application.
    It hooks into Textual's render cycle and draws images after Textual
    has finished its own rendering.
    """

    _instance: ImageOverlayRenderer | None = None

    def __new__(cls) -> Self:
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the image overlay renderer."""
        if self._initialized:
            return
        self._initialized = True
        self._pending_images: list[ImageRequest] = []
        self._capability = detect_image_capability()
        self._last_rendered: list[ImageRequest] = []

    @contextlib.contextmanager
    def _get_tty(self) -> Iterator[TextIO]:
        """Get TTY for direct terminal writes as a context manager."""
        tty: TextIO | None = None
        try:
            tty = open("/dev/tty", "w")  # noqa: SIM115
            yield tty
        except OSError:
            yield sys.stdout
        finally:
            if tty is not None and tty is not sys.stdout:
                tty.close()

    @property
    def supports_native_images(self) -> bool:
        """Check if terminal supports native image protocols."""
        return self._capability in (
            ImageCapability.KITTY,
            ImageCapability.ITERM,
            ImageCapability.SIXEL,
        )

    def queue_image(
        self,
        path: Path,
        row: int,
        col: int,
        width: int,
        height: int,
    ) -> None:
        """Queue an image to be rendered at the specified position.

        Args:
            path: Path to the image file.
            row: Screen row (1-based).
            col: Screen column (1-based).
            width: Width in characters.
            height: Height in lines.

        """
        self._pending_images.append(
            ImageRequest(path=path, row=row, col=col, width=width, height=height)
        )

    def clear_queue(self) -> None:
        """Clear all pending image requests."""
        self._pending_images.clear()

    def render_pending(self) -> None:
        """Render all pending images to the terminal.

        This should be called after Textual has finished rendering.
        """
        if not self._pending_images:
            return

        if not self.supports_native_images:
            self._pending_images.clear()
            return

        # Write directly to TTY to bypass Textual's output handling
        with self._get_tty() as tty:
            # Save cursor position
            tty.write("\x1b[s")

            for request in self._pending_images:
                self._render_image(request, tty)

            # Restore cursor position
            tty.write("\x1b[u")
            tty.flush()

        self._last_rendered = self._pending_images.copy()
        self._pending_images.clear()

    def clear_images(self) -> None:
        """Clear previously rendered images from the screen.

        This should be called before Textual re-renders to avoid artifacts.
        """
        if not self._last_rendered:
            return

        # For Kitty, we can delete images by ID
        # For iTerm2 and Sixel, we just let Textual overwrite them
        if self._capability == ImageCapability.KITTY:
            # Delete all images
            with self._get_tty() as tty:
                tty.write("\x1b_Ga=d\x1b\\")
                tty.flush()

        self._last_rendered.clear()

    def rerender_last(self) -> None:
        """Re-render the last rendered images.

        Call this periodically to keep images visible after Textual redraws.
        """
        if not self._last_rendered or not self.supports_native_images:
            return

        with self._get_tty() as tty:
            # Save cursor position
            tty.write("\x1b[s")

            for request in self._last_rendered:
                self._render_image_quiet(request, tty)

            # Restore cursor position
            tty.write("\x1b[u")
            tty.flush()

    def _render_image_quiet(self, request: ImageRequest, tty) -> None:
        """Render a single image without debug logging."""
        if not request.path.exists():
            return

        # Move cursor to position
        tty.write(f"\x1b[{request.row};{request.col}H")

        # Render using appropriate protocol
        if self._capability == ImageCapability.ITERM:
            self._render_iterm_quiet(request, tty)
        elif self._capability == ImageCapability.KITTY:
            self._render_kitty(request, tty)
        elif self._capability == ImageCapability.SIXEL:
            self._render_sixel(request, tty)

    def _render_iterm_quiet(self, request: ImageRequest, tty) -> None:
        """Render iTerm2 image without debug logging."""
        import base64

        with open(request.path, "rb") as f:
            raw_data = f.read()
            image_data = base64.b64encode(raw_data).decode("ascii")

        params = (
            f"name={base64.b64encode(request.path.name.encode()).decode('ascii')};"
            f"size={len(raw_data)};"
            f"width={request.width};"
            f"height={request.height};"
            f"inline=1;"
            f"preserveAspectRatio=1"
        )
        tty.write(f"\x1b]1337;File={params}:{image_data}\x07")
        tty.flush()

    def _render_image(self, request: ImageRequest, tty) -> None:
        """Render a single image at its specified position."""
        if not request.path.exists():
            return

        # Move cursor to position
        tty.write(f"\x1b[{request.row};{request.col}H")

        # Render using appropriate protocol
        if self._capability == ImageCapability.ITERM:
            self._render_iterm(request, tty)
        elif self._capability == ImageCapability.KITTY:
            self._render_kitty(request, tty)
        elif self._capability == ImageCapability.SIXEL:
            self._render_sixel(request, tty)

    def _render_iterm(self, request: ImageRequest, tty) -> None:
        """Render image using iTerm2 inline image protocol."""
        import base64

        with open(request.path, "rb") as f:
            raw_data = f.read()
            image_data = base64.b64encode(raw_data).decode("ascii")

        # iTerm2 inline image protocol
        # Width and height in cells
        params = (
            f"name={base64.b64encode(request.path.name.encode()).decode('ascii')};"
            f"size={len(raw_data)};"
            f"width={request.width};"
            f"height={request.height};"
            f"inline=1;"
            f"preserveAspectRatio=1"
        )
        escape_seq = f"\x1b]1337;File={params}:{image_data}\x07"
        tty.write(escape_seq)
        tty.flush()

    def _render_kitty(self, request: ImageRequest, tty) -> None:
        """Render image using Kitty graphics protocol."""
        import base64

        with open(request.path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("ascii")

        # Kitty graphics protocol
        # a=T: transmit and display
        # f=100: PNG format (auto-detect)
        # c=width, r=height in cells
        chunk_size = 4096
        chunks = [
            image_data[i : i + chunk_size]
            for i in range(0, len(image_data), chunk_size)
        ]

        for i, chunk in enumerate(chunks):
            is_last = i == len(chunks) - 1
            m = 0 if is_last else 1  # m=1 means more chunks coming

            if i == 0:
                # First chunk includes parameters
                tty.write(
                    f"\x1b_Ga=T,f=100,c={request.width},r={request.height},m={m};"
                    f"{chunk}\x1b\\"
                )
            else:
                tty.write(f"\x1b_Gm={m};{chunk}\x1b\\")

    def _render_sixel(self, request: ImageRequest, tty) -> None:
        """Render image using Sixel graphics."""
        from .sixel import SixelRenderer

        renderer = SixelRenderer()
        sixel_data = renderer.render(request.path, request.width, request.height)
        tty.write(sixel_data)


def get_overlay_renderer() -> ImageOverlayRenderer:
    """Get the singleton overlay renderer instance."""
    return ImageOverlayRenderer()
