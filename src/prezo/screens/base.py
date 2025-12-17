"""Base screen classes for Prezo."""

from __future__ import annotations

from typing import Generic, TypeVar

from textual.screen import ModalScreen

from prezo.themes import Theme, get_theme

ResultType = TypeVar("ResultType")


class ThemedModalScreen(ModalScreen, Generic[ResultType]):
    """Base modal screen that applies the current app theme."""

    def on_mount(self) -> None:
        """Apply theme when mounted."""
        self._apply_theme()

    def _apply_theme(self) -> None:
        """Apply the current app theme to this modal."""
        # Get the current theme from the app
        theme_name = getattr(self.app, "app_theme", "dark")
        theme = get_theme(theme_name)

        # Apply theme to common container elements
        self._apply_theme_to_containers(theme)

    def _apply_theme_to_containers(self, theme: Theme) -> None:
        """Apply theme colors to container elements.

        Override this in subclasses for custom theming.
        """
        # Apply to container elements
        for container_id in [
            "help-container",
            "overview-container",
            "toc-container",
            "search-container",
            "goto-container",
        ]:
            containers = self.query(f"#{container_id}")
            for container in containers:
                container.styles.background = theme.surface
                container.styles.border = ("solid", theme.primary)

        # Apply to title elements
        for title_id in [
            "help-title",
            "overview-title",
            "toc-title",
            "search-title",
            "goto-title",
        ]:
            titles = self.query(f"#{title_id}")
            for title in titles:
                title.styles.background = theme.primary
                title.styles.color = theme.text

        # Apply to hint elements
        for hint_id in ["toc-hint", "search-hint", "goto-hint"]:
            hints = self.query(f"#{hint_id}")
            for hint in hints:
                hint.styles.color = theme.text_muted
