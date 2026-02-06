"""Theme definitions for Prezo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config, CustomTheme


@dataclass
class Theme:
    """A color theme for the presentation viewer."""

    name: str
    primary: str
    secondary: str
    background: str
    surface: str
    text: str
    text_muted: str
    success: str
    warning: str
    error: str


# Built-in themes
_BUILTIN_THEMES: dict[str, Theme] = {
    "dark": Theme(
        name="dark",
        primary="#0178d4",
        secondary="#6f42c1",
        background="#121212",
        surface="#1e1e1e",
        text="#e0e0e0",
        text_muted="#888888",
        success="#28a745",
        warning="#ffc107",
        error="#dc3545",
    ),
    "light": Theme(
        name="light",
        primary="#0066cc",
        secondary="#6f42c1",
        background="#ffffff",
        surface="#f5f5f5",
        text="#1a1a1a",
        text_muted="#666666",
        success="#28a745",
        warning="#ffc107",
        error="#dc3545",
    ),
    "dracula": Theme(
        name="dracula",
        primary="#bd93f9",
        secondary="#ff79c6",
        background="#282a36",
        surface="#44475a",
        text="#f8f8f2",
        text_muted="#6272a4",
        success="#50fa7b",
        warning="#f1fa8c",
        error="#ff5555",
    ),
    "solarized-dark": Theme(
        name="solarized-dark",
        primary="#268bd2",
        secondary="#2aa198",
        background="#002b36",
        surface="#073642",
        text="#839496",
        text_muted="#586e75",
        success="#859900",
        warning="#b58900",
        error="#dc322f",
    ),
    "nord": Theme(
        name="nord",
        primary="#88c0d0",
        secondary="#81a1c1",
        background="#2e3440",
        surface="#3b4252",
        text="#eceff4",
        text_muted="#7b88a1",
        success="#a3be8c",
        warning="#ebcb8b",
        error="#bf616a",
    ),
    "gruvbox": Theme(
        name="gruvbox",
        primary="#83a598",
        secondary="#d3869b",
        background="#282828",
        surface="#3c3836",
        text="#ebdbb2",
        text_muted="#928374",
        success="#b8bb26",
        warning="#fabd2f",
        error="#fb4934",
    ),
}

_BUILTIN_THEME_ORDER = ["dark", "light", "dracula", "solarized-dark", "nord", "gruvbox"]

# Mutable theme registry (builtins + custom themes)
THEMES: dict[str, Theme] = dict(_BUILTIN_THEMES)
THEME_ORDER: list[str] = list(_BUILTIN_THEME_ORDER)


def register_custom_themes(config: Config) -> None:
    """Register custom themes from configuration.

    Custom themes are added to the theme registry and cycle order.
    They can override builtin themes or define entirely new ones.

    Args:
        config: Configuration containing custom_themes dict.

    """
    for name, custom_theme in config.custom_themes.items():
        theme = _custom_theme_to_theme(name, custom_theme)
        THEMES[name] = theme
        if name not in THEME_ORDER:
            THEME_ORDER.append(name)


def _custom_theme_to_theme(name: str, custom: CustomTheme) -> Theme:
    """Convert a CustomTheme from config to a Theme object.

    Missing colors are inherited from the 'dark' theme.
    """
    base = _BUILTIN_THEMES["dark"]
    return Theme(
        name=name,
        primary=custom.primary or base.primary,
        secondary=custom.secondary or base.secondary,
        background=custom.background or base.background,
        surface=custom.surface or base.surface,
        text=custom.text or base.text,
        text_muted=custom.text_muted or base.text_muted,
        success=custom.success or base.success,
        warning=custom.warning or base.warning,
        error=custom.error or base.error,
    )


def get_theme(name: str) -> Theme:
    """Get a theme by name, defaulting to 'dark'."""
    return THEMES.get(name, THEMES["dark"])


def get_next_theme(current: str) -> str:
    """Get the next theme name in the cycle."""
    try:
        idx = THEME_ORDER.index(current)
        return THEME_ORDER[(idx + 1) % len(THEME_ORDER)]
    except ValueError:
        return THEME_ORDER[0]


def theme_to_css(theme: Theme) -> str:
    """Generate Textual CSS variables from a theme."""
    return f"""
    $primary: {theme.primary};
    $secondary: {theme.secondary};
    $background: {theme.background};
    $surface: {theme.surface};
    $text: {theme.text};
    $text-muted: {theme.text_muted};
    $success: {theme.success};
    $warning: {theme.warning};
    $error: {theme.error};
    """
