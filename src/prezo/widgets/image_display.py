"""Image display widget for Prezo.

Uses textual-image for native terminal graphics protocol support (Kitty, Sixel).
Falls back to Unicode halfcell rendering for unsupported terminals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.widgets import Static
from textual_image.widget import Image as TextualImage

if TYPE_CHECKING:
    from pathlib import Path

    from textual.app import ComposeResult


class ImageDisplay(Static):
    """Widget that displays images in the terminal.

    Uses textual-image library which supports:
    - Kitty Terminal Graphics Protocol (TGP)
    - Sixel graphics (iTerm2, WezTerm, xterm, etc.)
    - Unicode halfcell fallback for other terminals

    This is a container widget that wraps textual_image.widget.Image
    to provide a consistent API for Prezo.
    """

    DEFAULT_CSS = """
    ImageDisplay {
        width: 100%;
        height: auto;
        min-height: 10;
        padding: 0;
    }

    ImageDisplay > Image {
        width: 100%;
        height: auto;
    }
    """

    def __init__(
        self,
        image_path: Path | str | None = None,
        *,
        width: int | None = None,
        height: int | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the image display widget.

        Args:
            image_path: Path to the image file.
            width: Width in characters (None = auto).
            height: Height in characters (None = auto).
            name: Widget name.
            id: Widget ID.
            classes: CSS classes.

        """
        super().__init__(name=name, id=id, classes=classes)
        self._image_path: Path | str | None = image_path
        self._width: int | None = width
        self._height: int | None = height
        self._image_widget: Any = None  # TextualImage | None

    def compose(self) -> ComposeResult:
        """Compose the image widget."""
        self._image_widget = TextualImage(self._image_path)
        self._apply_dimensions()
        yield self._image_widget

    def _apply_dimensions(self) -> None:
        """Apply width/height dimensions to the image widget."""
        if self._image_widget is None:
            return

        # Apply width if specified
        if self._width is not None:
            self._image_widget.styles.width = self._width
        # Apply height if specified
        if self._height is not None:
            self._image_widget.styles.height = self._height

    def set_image(
        self,
        path: Path | str | None,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Set the image to display.

        Args:
            path: Path to the image file, or None to clear.
            width: Width in characters (None = auto).
            height: Height in characters (None = auto).

        """
        self._image_path = path
        self._width = width
        self._height = height
        if self._image_widget is not None:
            self._image_widget.image = path
            self._apply_dimensions()

    def clear(self) -> None:
        """Clear the image display."""
        self._image_path = None
        if self._image_widget is not None:
            self._image_widget.image = None
