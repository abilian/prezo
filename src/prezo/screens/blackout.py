"""Blackout screen for Prezo."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.screen import ModalScreen
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class BlackoutScreen(ModalScreen[None]):
    """Modal screen for blacking out the display during presentation pauses."""

    CSS = """
    BlackoutScreen {
        background: black;
    }

    #blackout-hint {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: #333;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss", "Return", show=False),
        Binding("b", "dismiss", "Return", show=False),
        Binding("space", "dismiss", "Return", show=False),
        Binding("enter", "dismiss", "Return", show=False),
    ]

    def __init__(self, white: bool = False) -> None:
        """Initialize the blackout screen.

        Args:
            white: If True, show white screen instead of black.

        """
        super().__init__()
        self.white = white

    def compose(self) -> ComposeResult:
        """Compose the blackout screen layout."""
        yield Static("Press any key to return", id="blackout-hint")

    def on_mount(self) -> None:
        """Apply white theme if configured."""
        if self.white:
            self.styles.background = "white"
            self.query_one("#blackout-hint").styles.color = "#ccc"

    def on_key(self) -> None:
        """Dismiss the screen on any key press."""
        self.dismiss(None)
