"""Table of Contents screen for prezo."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import VerticalScroll
from textual.widgets import Static

from .base import ThemedModalScreen

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from prezo.parser import Presentation


class TocEntry(Static):
    """A single TOC entry."""

    def __init__(
        self,
        slide_index: int,
        title: str,
        level: int,
        is_current: bool = False,
        **kwargs,
    ) -> None:
        """Initialize a TOC entry.

        Args:
            slide_index: Index of the slide this entry refers to.
            title: Title text for the entry.
            level: Heading level (1-6) for indentation.
            is_current: Whether this is the current slide.
            **kwargs: Additional arguments for Static widget.

        """
        super().__init__(**kwargs)
        self.slide_index = slide_index
        self.title = title
        self.level = level
        self.is_current = is_current

    def render(self) -> str:
        """Render the TOC entry with indentation and marker."""
        indent = "  " * (self.level - 1)
        marker = "►" if self.is_current else " "
        return f"{marker} {indent}{self.title} ({self.slide_index + 1})"


class TableOfContentsScreen(ThemedModalScreen[int | None]):
    """Modal screen showing table of contents based on headings."""

    CSS = """
    TableOfContentsScreen {
        align: center middle;
    }

    #toc-container {
        width: 70%;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #toc-title {
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $primary;
        color: $text;
        margin-bottom: 1;
    }

    #toc-list {
        width: 100%;
        height: 1fr;
    }

    .toc-entry {
        width: 100%;
        height: 1;
        padding: 0 1;
    }

    .toc-entry:hover {
        background: $primary-darken-2;
    }

    .toc-entry.selected {
        background: $primary;
    }

    .toc-entry.current {
        text-style: bold;
    }

    #toc-hint {
        width: 100%;
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("q", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
        Binding("space", "select", "Select", show=False),
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("j", "move_down", "Down", show=False),
        Binding("home", "first", "First", show=False),
        Binding("end", "last", "Last", show=False),
    ]

    def __init__(self, presentation: Presentation, current_slide: int) -> None:
        """Initialize the table of contents screen.

        Args:
            presentation: The presentation to build TOC from.
            current_slide: Index of the currently active slide.

        """
        super().__init__()
        self.presentation = presentation
        self.current_slide = current_slide
        self.entries: list[tuple[int, str, int]] = []  # (slide_index, title, level)
        self.selected_index = 0
        self._build_toc()

    def _build_toc(self) -> None:
        """Build table of contents from slide headings."""
        for i, slide in enumerate(self.presentation.slides):
            heading = self._extract_heading(slide.content)
            if heading:
                title, level = heading
                self.entries.append((i, title, level))

        # If no headings found, create entries for all slides
        if not self.entries:
            for i, slide in enumerate(self.presentation.slides):
                title = self._get_first_line(slide.content)
                self.entries.append((i, title, 1))

        # Set initial selection to current slide's entry
        for idx, (slide_idx, _, _) in enumerate(self.entries):
            if slide_idx >= self.current_slide:
                self.selected_index = idx
                break

    def _extract_heading(self, content: str) -> tuple[str, int] | None:
        """Extract first heading and its level from content."""
        for line in content.strip().split("\n"):
            line = line.strip()
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                # Remove markdown formatting
                title = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", title)
                return title[:60], level
        return None

    def _get_first_line(self, content: str) -> str:
        """Get first non-empty line of content."""
        for line in content.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("<!--"):
                return line[:60]
        return "Untitled"

    def compose(self) -> ComposeResult:
        """Compose the table of contents layout."""
        with VerticalScroll(id="toc-container"):
            yield Static(" Table of Contents ", id="toc-title")
            with VerticalScroll(id="toc-list"):
                for idx, (slide_idx, title, level) in enumerate(self.entries):
                    is_current = slide_idx == self.current_slide
                    classes = "toc-entry"
                    if idx == self.selected_index:
                        classes += " selected"
                    if is_current:
                        classes += " current"
                    yield TocEntry(slide_idx, title, level, is_current, classes=classes)
            yield Static("Enter to jump, Esc to cancel", id="toc-hint")

    def on_mount(self) -> None:
        """Scroll to the selected entry on mount."""
        super().on_mount()
        self._scroll_to_selected()

    def _update_selection(self) -> None:
        """Update visual selection."""
        toc_list = self.query_one("#toc-list", VerticalScroll)
        for idx, child in enumerate(toc_list.query(".toc-entry")):
            if idx == self.selected_index:
                child.add_class("selected")
                child.scroll_visible()
            else:
                child.remove_class("selected")

    def _scroll_to_selected(self) -> None:
        """Scroll to show the selected entry."""
        toc_list = self.query_one("#toc-list", VerticalScroll)
        entries = list(toc_list.query(".toc-entry"))
        if 0 <= self.selected_index < len(entries):
            entries[self.selected_index].scroll_visible()

    def action_cancel(self) -> None:
        """Cancel and dismiss the TOC screen."""
        self.dismiss(None)

    def action_select(self) -> None:
        """Select the currently highlighted TOC entry."""
        if 0 <= self.selected_index < len(self.entries):
            self.dismiss(self.entries[self.selected_index][0])
        else:
            self.dismiss(None)

    def action_move_up(self) -> None:
        """Move selection up in the TOC list."""
        if self.selected_index > 0:
            self.selected_index -= 1
            self._update_selection()

    def action_move_down(self) -> None:
        """Move selection down in the TOC list."""
        if self.selected_index < len(self.entries) - 1:
            self.selected_index += 1
            self._update_selection()

    def action_first(self) -> None:
        """Jump to first TOC entry."""
        self.selected_index = 0
        self._update_selection()

    def action_last(self) -> None:
        """Jump to last TOC entry."""
        self.selected_index = len(self.entries) - 1
        self._update_selection()

    def on_click(self, event) -> None:
        """Handle clicking on a TOC entry."""
        widget = self.get_widget_at(event.screen_x, event.screen_y)
        if widget and isinstance(widget, TocEntry):
            self.dismiss(widget.slide_index)
