"""Slide content widget with layout support."""

from __future__ import annotations

from textual.widgets import Static

from prezo.layout import (
    has_layout_blocks,
    parse_layout,
    render_layout,
    render_styled_markdown,
)


class SlideContent(Static):
    """Widget that renders slide content with optional layout support.

    Handles both plain markdown and Pandoc-style fenced div layouts:
    - Plain markdown is rendered with styled H1/H2 (heavy box, centered)
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
        super().__init__("", name=name, id=id, classes=classes)
        self._raw_content = content
        if content:
            self._update_renderable()

    def _get_primary_color(self) -> str:
        """Get the primary color from the app's theme."""
        from prezo.themes import THEMES

        try:
            if self.is_attached:
                theme_name = getattr(self.app, "app_theme", None)
                if theme_name:
                    theme = THEMES.get(theme_name)
                    if theme:
                        return theme.primary
        except Exception:
            pass
        return "#0178d4"  # Default blue

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

        primary_color = self._get_primary_color()

        # Check for layout directives
        if has_layout_blocks(self._raw_content):
            blocks = parse_layout(self._raw_content)
            renderable = render_layout(blocks, primary_color=primary_color)
        else:
            # Plain markdown with styled headings
            renderable = render_styled_markdown(self._raw_content, primary_color)

        super().update(renderable)
