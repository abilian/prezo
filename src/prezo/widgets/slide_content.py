"""Slide content widget with layout support."""

from __future__ import annotations

from rich.markdown import Markdown as RichMarkdown
from textual.widgets import Static

from prezo.layout import has_layout_blocks, parse_layout, render_layout


class SlideContent(Static):
    """Widget that renders slide content with optional layout support.

    Handles both plain markdown and Pandoc-style fenced div layouts:
    - Plain markdown is rendered using Rich's Markdown
    - Layout blocks (columns, center) are rendered using the layout module

    Inherits from Static to properly handle Rich renderable display.
    """

    DEFAULT_CSS = """
    SlideContent {
        width: 100%;
        height: auto;
    }
    """

    def __init__(
        self,
        content: str = "",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the slide content widget.

        Args:
            content: Markdown content to display.
            name: Widget name.
            id: Widget ID.
            classes: CSS classes.

        """
        # Initialize Static with the rendered content
        super().__init__("", name=name, id=id, classes=classes)
        self._raw_content = content
        if content:
            self._update_renderable()

    @property
    def raw_content(self) -> str:
        """Get the current raw markdown content."""
        return self._raw_content

    def set_content(self, content: str) -> None:
        """Set the markdown content and refresh the widget.

        Args:
            content: New markdown content to display.

        """
        self._raw_content = content
        self._update_renderable()

    def _update_renderable(self) -> None:
        """Update the internal renderable based on content."""
        if not self._raw_content:
            super().update("")
            return

        # Check for layout directives
        if has_layout_blocks(self._raw_content):
            blocks = parse_layout(self._raw_content)
            renderable = render_layout(blocks)
        else:
            # Plain markdown
            renderable = RichMarkdown(self._raw_content)

        # Use Static's update to set the renderable
        super().update(renderable)
