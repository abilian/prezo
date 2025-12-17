"""Slide button widget for overview grid."""

from __future__ import annotations

import re

from textual.widgets import Button

MAX_TITLE_LENGTH = 35


def extract_slide_title(content: str, slide_index: int) -> str:
    """Extract the first heading (any level) from slide content.

    Args:
        content: Slide markdown content
        slide_index: Zero-based slide index (for fallback title)

    Returns:
        Extracted or generated title, truncated to MAX_TITLE_LENGTH

    """
    for line in content.strip().split("\n"):
        line = line.strip()
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            title = match.group(2).strip()
            title = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", title)
            return _truncate(title)

    for line in content.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("<!--"):
            return _truncate(line)

    return f"Slide {slide_index + 1}"


def _truncate(text: str) -> str:
    """Truncate text to MAX_TITLE_LENGTH with ellipsis if needed."""
    if len(text) > MAX_TITLE_LENGTH:
        return text[: MAX_TITLE_LENGTH - 3] + "..."
    return text


class SlideButton(Button):
    """A button representing a slide in the overview grid."""

    def __init__(
        self,
        slide_index: int,
        content: str,
        *,
        is_current: bool = False,
    ) -> None:
        """Initialize a slide button.

        Args:
            slide_index: Zero-based index of the slide.
            content: Markdown content of the slide.
            is_current: Whether this is the currently active slide.

        """
        title = extract_slide_title(content, slide_index)
        super().__init__(title, id=f"slide-{slide_index}")
        self.slide_index = slide_index
        self.is_current = is_current

    def on_mount(self) -> None:
        """Add current class if this is the active slide."""
        if self.is_current:
            self.add_class("current")
