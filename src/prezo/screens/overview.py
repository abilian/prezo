"""Slide overview screen for prezo."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Grid, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from prezo.widgets import SlideButton

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from prezo.parser import Presentation


class SlideOverviewScreen(ModalScreen[int | None]):
    """Modal screen showing grid overview of all slides."""

    GRID_COLUMNS = 4  # Number of columns in the grid

    CSS = """
    SlideOverviewScreen {
        align: center middle;
    }

    #overview-container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #overview-title {
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    #slide-grid {
        width: 100%;
        height: 1fr;
        grid-size: 4;
        grid-gutter: 1;
        padding: 1;
        overflow-y: auto;
    }

    SlideButton {
        width: 100%;
        height: 3;
    }

    SlideButton.current {
        background: $success;
    }

    SlideButton:focus {
        background: $primary;
    }

    SlideButton.current:focus {
        background: $success-darken-1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("q", "cancel", "Cancel"),
        Binding("enter", "select", "Select", show=True),
        Binding("space", "select", "Select", show=False),
        Binding("left", "move(-1, 0)", "Left", show=False),
        Binding("right", "move(1, 0)", "Right", show=False),
        Binding("up", "move(0, -1)", "Up", show=False),
        Binding("down", "move(0, 1)", "Down", show=False),
        Binding("h", "move(-1, 0)", "Left", show=False),
        Binding("l", "move(1, 0)", "Right", show=False),
        Binding("k", "move(0, -1)", "Up", show=False),
        Binding("j", "move(0, 1)", "Down", show=False),
        Binding("home", "first", "First", show=False),
        Binding("end", "last", "Last", show=False),
    ]

    def __init__(self, presentation: Presentation, current_slide: int) -> None:
        """Initialize the slide overview screen.

        Args:
            presentation: The presentation to display.
            current_slide: Index of the currently active slide.

        """
        super().__init__()
        self.presentation = presentation
        self.current_slide = current_slide
        self.selected_index = current_slide

    def compose(self) -> ComposeResult:
        """Compose the overview grid layout."""
        with VerticalScroll(id="overview-container"):
            yield Static(
                " Slide Overview (Enter to jump, Esc to cancel) ",
                id="overview-title",
            )
            with Grid(id="slide-grid"):
                for i, slide in enumerate(self.presentation.slides):
                    yield SlideButton(
                        i,
                        slide.content,
                        is_current=(i == self.current_slide),
                    )

    def on_mount(self) -> None:
        """Focus the current slide button on mount."""
        self._focus_selected()

    def _focus_selected(self) -> None:
        """Focus the currently selected slide button."""
        try:
            button = self.query_one(f"#slide-{self.selected_index}", SlideButton)
            button.focus()
            button.scroll_visible()
        except (KeyError, LookupError):
            # Button not found - can happen during initialization
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle slide button press to navigate to that slide."""
        if isinstance(event.button, SlideButton):
            self.dismiss(event.button.slide_index)

    def action_cancel(self) -> None:
        """Cancel and dismiss the overview."""
        self.dismiss(None)

    def action_select(self) -> None:
        """Select the currently focused slide."""
        self.dismiss(self.selected_index)

    def action_move(self, dx: int, dy: int) -> None:
        """Move selection in the grid."""
        total = self.presentation.total_slides
        cols = self.GRID_COLUMNS

        # Calculate new position
        row = self.selected_index // cols
        col = self.selected_index % cols

        new_col = col + dx
        new_row = row + dy

        # Handle horizontal wrapping
        if new_col < 0:
            new_col = cols - 1
            new_row -= 1
        elif new_col >= cols:
            new_col = 0
            new_row += 1

        # Calculate new index
        new_index = new_row * cols + new_col

        # Clamp to valid range
        if 0 <= new_index < total:
            self.selected_index = new_index
            self._focus_selected()

    def action_first(self) -> None:
        """Jump to first slide."""
        self.selected_index = 0
        self._focus_selected()

    def action_last(self) -> None:
        """Jump to last slide."""
        self.selected_index = self.presentation.total_slides - 1
        self._focus_selected()
