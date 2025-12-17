"""Go-to-slide screen for Prezo."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.widgets import Input, Static

from .base import ThemedModalScreen

if TYPE_CHECKING:
    from textual.app import ComposeResult


class GotoSlideScreen(ThemedModalScreen[int | None]):
    """Modal screen for jumping to a specific slide number."""

    CSS = """
    GotoSlideScreen {
        align: center middle;
    }

    #goto-container {
        width: 40;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #goto-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #goto-input {
        width: 100%;
    }

    #goto-hint {
        width: 100%;
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, total_slides: int) -> None:
        """Initialize the go-to-slide screen.

        Args:
            total_slides: Total number of slides in the presentation.

        """
        super().__init__()
        self.total_slides = total_slides

    def compose(self) -> ComposeResult:
        """Compose the go-to-slide dialog layout."""
        with Vertical(id="goto-container"):
            yield Static("Go to slide", id="goto-title")
            yield Input(placeholder=f"1-{self.total_slides}", id="goto-input")
            yield Static(f"Enter slide number (1-{self.total_slides})", id="goto-hint")

    def on_mount(self) -> None:
        """Focus the input field on mount."""
        super().on_mount()
        self.query_one("#goto-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission and navigate to the specified slide."""
        value = event.value.strip()
        if not value:
            self.dismiss(None)
            return

        try:
            slide_num = int(value)
            if 1 <= slide_num <= self.total_slides:
                self.dismiss(slide_num - 1)  # Convert to 0-indexed
            else:
                self.notify(
                    f"Invalid slide number. Enter 1-{self.total_slides}",
                    severity="error",
                )
        except ValueError:
            self.notify("Please enter a valid number", severity="error")

    def action_cancel(self) -> None:
        """Cancel and dismiss the dialog."""
        self.dismiss(None)
