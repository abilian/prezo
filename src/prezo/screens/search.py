"""Slide search screen for prezo."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Input, Static

from .base import ThemedModalScreen

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from prezo.parser import Presentation


class SearchResultItem(Static):
    """A single search result item."""

    def __init__(self, slide_index: int, title: str, context: str, **kwargs) -> None:
        """Initialize a search result item.

        Args:
            slide_index: Index of the slide this result refers to.
            title: Title of the slide.
            context: Context text showing the search match.
            **kwargs: Additional arguments for Static widget.

        """
        super().__init__(**kwargs)
        self.slide_index = slide_index
        self.title = title
        self.context = context

    def render(self) -> str:
        """Render the search result item."""
        return f"[{self.slide_index + 1}] {self.title}\n    {self.context}"


class SlideSearchScreen(ThemedModalScreen[int | None]):
    """Modal screen for searching slides by content."""

    CSS = """
    SlideSearchScreen {
        align: center middle;
    }

    #search-container {
        width: 80%;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #search-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #search-input {
        width: 100%;
        margin-bottom: 1;
    }

    #search-results {
        width: 100%;
        height: 1fr;
        border: solid $primary-darken-2;
        padding: 1;
    }

    .search-result {
        width: 100%;
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }

    .search-result:hover {
        background: $primary-darken-2;
    }

    .search-result.selected {
        background: $primary;
    }

    #no-results {
        width: 100%;
        text-align: center;
        color: $text-muted;
        padding: 2;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("ctrl+p", "move_up", "Up", show=False),
        Binding("ctrl+n", "move_down", "Down", show=False),
    ]

    def __init__(self, presentation: Presentation) -> None:
        """Initialize the search screen.

        Args:
            presentation: The presentation to search through.

        """
        super().__init__()
        self.presentation = presentation
        self.results: list[int] = []  # Slide indices
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        """Compose the search screen layout."""
        with Vertical(id="search-container"):
            yield Static("Search Slides", id="search-title")
            yield Input(placeholder="Type to search...", id="search-input")
            with VerticalScroll(id="search-results"):
                yield Static("Type to search slide content", id="no-results")

    def on_mount(self) -> None:
        """Focus the search input on mount."""
        super().on_mount()
        self.query_one("#search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes to perform live search."""
        self._perform_search(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the search input."""
        self.action_select()

    def _perform_search(self, query: str) -> None:
        """Search slides for the query string."""
        results_container = self.query_one("#search-results", VerticalScroll)

        # Clear previous results
        for child in list(results_container.children):
            child.remove()

        if not query.strip():
            results_container.mount(
                Static("Type to search slide content", id="no-results"),
            )
            self.results = []
            return

        query_lower = query.lower()
        self.results = []

        for i, slide in enumerate(self.presentation.slides):
            if (
                query_lower in slide.content.lower()
                or query_lower in slide.raw_content.lower()
            ):
                self.results.append(i)

        if not self.results:
            results_container.mount(
                Static(f"No results for '{query}'", id="no-results"),
            )
            return

        self.selected_index = 0
        for idx, slide_idx in enumerate(self.results):
            slide = self.presentation.slides[slide_idx]
            title = self._extract_title(slide.content)
            context = self._extract_context(slide.content, query_lower)

            item = SearchResultItem(
                slide_idx,
                title,
                context,
                classes="search-result" + (" selected" if idx == 0 else ""),
            )
            results_container.mount(item)

    def _extract_title(self, content: str) -> str:
        """Extract title from slide content."""
        for line in content.strip().split("\n"):
            line = line.strip()
            match = re.match(r"^#{1,6}\s+(.+)$", line)
            if match:
                return match.group(1).strip()[:50]
        return content.strip().split("\n")[0][:50] if content.strip() else "Untitled"

    def _extract_context(self, content: str, query: str) -> str:
        """Extract context around the search match."""
        content_lower = content.lower()
        pos = content_lower.find(query)
        if pos == -1:
            return ""

        start = max(0, pos - 20)
        end = min(len(content), pos + len(query) + 30)

        context = content[start:end].replace("\n", " ")
        if start > 0:
            context = "..." + context
        if end < len(content):
            context = context + "..."

        return context

    def _update_selection(self) -> None:
        """Update visual selection."""
        results_container = self.query_one("#search-results", VerticalScroll)
        for idx, child in enumerate(results_container.query(".search-result")):
            if idx == self.selected_index:
                child.add_class("selected")
                child.scroll_visible()
            else:
                child.remove_class("selected")

    def action_cancel(self) -> None:
        """Cancel and dismiss the search screen."""
        self.dismiss(None)

    def action_select(self) -> None:
        """Select the currently highlighted search result."""
        if self.results and 0 <= self.selected_index < len(self.results):
            self.dismiss(self.results[self.selected_index])
        else:
            self.dismiss(None)

    def action_move_up(self) -> None:
        """Move selection up in the results list."""
        if self.results and self.selected_index > 0:
            self.selected_index -= 1
            self._update_selection()

    def action_move_down(self) -> None:
        """Move selection down in the results list."""
        if self.results and self.selected_index < len(self.results) - 1:
            self.selected_index += 1
            self._update_selection()

    def on_click(self, event) -> None:
        """Handle clicking on a search result."""
        widget = self.get_widget_at(event.screen_x, event.screen_y)
        if widget and isinstance(widget, SearchResultItem):
            self.dismiss(widget.slide_index)
