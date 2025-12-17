"""Kitty terminal image renderer using the Kitty graphics protocol.

Kitty's protocol differs from iTerm2 in that images persist as overlays
managed by the terminal itself. They survive application redraws because
they're not part of the character buffer.

Reference: https://sw.kovidgoyal.net/kitty/graphics-protocol/
"""

from __future__ import annotations

import base64
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO

from typing_extensions import Self

from prezo.terminal import ImageCapability, detect_image_capability

if TYPE_CHECKING:
    from pathlib import Path


def is_kitty() -> bool:
    """Check if running in Kitty terminal."""
    return detect_image_capability() == ImageCapability.KITTY


@dataclass
class KittyImage:
    """A Kitty image with persistent ID."""

    id: int
    path: Path
    width: int
    height: int


class KittyImageManager:
    """Manages Kitty graphics protocol images with persistence.

    Images are transmitted once and persist in Kitty's memory.
    They can be repositioned or deleted without re-transmission.
    This allows images to coexist with Textual's rendering.
    """

    _instance: KittyImageManager | None = None
    _next_id: int = 1

    def __new__(cls) -> Self:
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the Kitty image manager."""
        if self._initialized:
            return
        self._initialized = True
        self._images: dict[int, KittyImage] = {}
        self._current_image_id: int | None = None
        self._path_to_id: dict[str, int] = {}  # Cache path -> id mapping

    def _get_tty(self) -> TextIO:
        """Get TTY for direct terminal writes."""
        try:
            return open("/dev/tty", "w")
        except OSError:
            return sys.stdout

    def _write(self, data: str) -> None:
        """Write directly to terminal."""
        tty = self._get_tty()
        tty.write(data)
        tty.flush()
        if tty is not sys.stdout:
            tty.close()

    def display_image(
        self,
        path: Path,
        row: int,
        col: int,
        width: int,
        height: int,
    ) -> int:
        """Display an image at a specific position.

        If the image was previously transmitted, reuses the cached version.

        Args:
            path: Path to image file.
            row: Screen row (1-based).
            col: Screen column (1-based).
            width: Display width in cells.
            height: Display height in cells.

        Returns:
            Image ID.

        """
        if not path.exists():
            return -1

        path_key = str(path.absolute())

        # Check if we already have this image
        if path_key in self._path_to_id:
            image_id = self._path_to_id[path_key]
            # Just reposition it
            self._position_image(image_id, row, col, width, height)
            self._current_image_id = image_id
            return image_id

        # Need to transmit new image
        image_id = self._transmit_and_display(path, row, col, width, height)
        if image_id > 0:
            self._path_to_id[path_key] = image_id
            self._current_image_id = image_id

        return image_id

    def _transmit_and_display(
        self,
        path: Path,
        row: int,
        col: int,
        width: int,
        height: int,
    ) -> int:
        """Transmit and display a new image.

        Args:
            path: Path to image file.
            row: Screen row (1-based).
            col: Screen column (1-based).
            width: Display width in cells.
            height: Display height in cells.

        Returns:
            Image ID for later reference.

        """
        # Generate unique ID
        image_id = KittyImageManager._next_id
        KittyImageManager._next_id += 1

        # Read and encode image
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")

        # Move cursor to position first
        self._write(f"\x1b[{row};{col}H")

        # Transmit and display in chunks
        # a=T: transmit and display
        # i=<id>: image ID for later reference
        # f=100: auto-detect format
        # c=cols, r=rows: size in cells
        # C=1: don't move cursor after display
        chunk_size = 4096
        chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

        for i, chunk in enumerate(chunks):
            is_last = i == len(chunks) - 1
            m = 0 if is_last else 1

            if i == 0:
                self._write(
                    f"\x1b_Ga=T,i={image_id},f=100,c={width},r={height},C=1,m={m};{chunk}\x1b\\"
                )
            else:
                self._write(f"\x1b_Gm={m};{chunk}\x1b\\")

        # Store reference
        self._images[image_id] = KittyImage(
            id=image_id, path=path, width=width, height=height
        )

        return image_id

    def _position_image(
        self,
        image_id: int,
        row: int,
        col: int,
        width: int,
        height: int,
    ) -> None:
        """Reposition an already-transmitted image.

        Args:
            image_id: ID from previous transmission.
            row: Screen row (1-based).
            col: Screen column (1-based).
            width: Display width in cells.
            height: Display height in cells.

        """
        if image_id not in self._images:
            return

        # Move cursor and display
        self._write(f"\x1b[{row};{col}H")
        # a=p: put/display previously transmitted image
        self._write(f"\x1b_Ga=p,i={image_id},c={width},r={height},C=1\x1b\\")

    def delete_image(self, image_id: int) -> None:
        """Delete a specific image from Kitty's memory."""
        if image_id not in self._images:
            return

        # a=d, d=I: delete by image ID
        self._write(f"\x1b_Ga=d,d=I,i={image_id}\x1b\\")

        # Clean up references
        img = self._images.pop(image_id)
        path_key = str(img.path.absolute())
        self._path_to_id.pop(path_key, None)

        if self._current_image_id == image_id:
            self._current_image_id = None

    def clear_visible(self) -> None:
        """Clear images from visible screen area (keeps them in memory)."""
        # a=d, d=a: delete all visible placements
        self._write("\x1b_Ga=d,d=a\x1b\\")

    def delete_all(self) -> None:
        """Delete all images from Kitty's memory."""
        # a=d, d=A: delete all images including data
        self._write("\x1b_Ga=d,d=A\x1b\\")
        self._images.clear()
        self._path_to_id.clear()
        self._current_image_id = None

    def hide_current(self) -> None:
        """Hide the currently displayed image (but keep in memory)."""
        if self._current_image_id is not None:
            # a=d, d=i: delete placement by ID (keeps image data)
            self._write(f"\x1b_Ga=d,d=i,i={self._current_image_id}\x1b\\")


def get_kitty_manager() -> KittyImageManager:
    """Get the singleton Kitty image manager."""
    return KittyImageManager()


class KittyRenderer:
    """Render images using Kitty's graphics protocol."""

    @property
    def name(self) -> str:
        """Get the renderer name."""
        return "kitty"

    def supports_inline(self) -> bool:
        """Kitty supports inline images."""
        return True

    def render(self, path: Path, width: int, height: int) -> str:
        """Render an image using Kitty graphics protocol.

        Args:
            path: Path to the image file.
            width: Target width in characters (cells).
            height: Target height in lines (cells).

        Returns:
            Escape sequence string to display the image.

        """
        try:
            return self._render_image(path, width, height)
        except Exception:
            from .ascii import AsciiRenderer

            return AsciiRenderer()._render_placeholder(path, width, height)

    def _render_image(self, path: Path, width: int, height: int) -> str:
        """Render image using Kitty protocol."""
        # Read and encode image
        image_data = path.read_bytes()
        encoded = base64.b64encode(image_data).decode("ascii")

        # Build Kitty graphics escape sequence
        # Format: \x1b_Ga=T,f=100,s=<w>,v=<h>,c=<cols>,r=<rows>;<base64>\x1b\\
        #
        # a=T: action = transmit and display
        # f=100: format = PNG (auto-detect)
        # c=cols: width in cells
        # r=rows: height in cells
        # m=1: more data follows (for chunked transfer)

        chunks = []
        chunk_size = 4096

        for i in range(0, len(encoded), chunk_size):
            chunk = encoded[i : i + chunk_size]
            is_last = i + chunk_size >= len(encoded)

            if i == 0:
                # First chunk includes all parameters
                params = f"a=T,f=100,c={width},r={height}"
                if not is_last:
                    params += ",m=1"
                chunks.append(f"\x1b_G{params};{chunk}\x1b\\")
            else:
                # Subsequent chunks
                m = "0" if is_last else "1"
                chunks.append(f"\x1b_Gm={m};{chunk}\x1b\\")

        return "".join(chunks)

    def render_file_direct(self, path: Path, width: int, height: int) -> str:
        """Render image by sending file path to Kitty.

        This is more efficient for local files as Kitty reads the file directly.

        Args:
            path: Path to the image file.
            width: Target width in cells.
            height: Target height in cells.

        Returns:
            Escape sequence string.

        """
        # Use file path transmission
        # a=T: transmit and display
        # t=f: transmission type = file
        # c, r: cell dimensions
        abs_path = str(path.absolute())
        encoded_path = base64.b64encode(abs_path.encode()).decode("ascii")

        return f"\x1b_Ga=T,t=f,c={width},r={height};{encoded_path}\x1b\\"

    def clear(self) -> str:
        """Return escape sequence to clear all Kitty images."""
        return "\x1b_Ga=d;\x1b\\"


def write_image_to_terminal(path: Path, width: int = 80, height: int = 24) -> None:
    """Write an image directly to the terminal.

    Utility function for direct terminal output.

    Args:
        path: Path to the image file.
        width: Target width in cells.
        height: Target height in cells.

    """
    renderer = KittyRenderer()
    output = renderer.render(path, width, height)
    sys.stdout.write(output)
    sys.stdout.flush()
