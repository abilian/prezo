"""Tests for theme functionality."""

from __future__ import annotations

from prezo.themes import THEME_ORDER, THEMES, get_next_theme, get_theme


class TestGetTheme:
    """Tests for get_theme function."""

    def test_get_dark_theme(self):
        theme = get_theme("dark")
        assert theme.name == "dark"
        assert theme.primary.startswith("#")

    def test_get_light_theme(self):
        theme = get_theme("light")
        assert theme.name == "light"

    def test_get_unknown_theme_returns_dark(self):
        theme = get_theme("nonexistent")
        assert theme.name == "dark"

    def test_all_themes_exist(self):
        for name in THEME_ORDER:
            theme = get_theme(name)
            assert theme.name == name


class TestGetNextTheme:
    """Tests for get_next_theme function."""

    def test_dark_to_light(self):
        assert get_next_theme("dark") == "light"

    def test_wraps_around(self):
        last_theme = THEME_ORDER[-1]
        assert get_next_theme(last_theme) == THEME_ORDER[0]

    def test_unknown_theme_returns_first(self):
        assert get_next_theme("nonexistent") == THEME_ORDER[0]


class TestThemeProperties:
    """Tests for theme data structure."""

    def test_all_themes_have_required_colors(self):
        for name, theme in THEMES.items():
            assert theme.primary, f"{name} missing primary"
            assert theme.background, f"{name} missing background"
            assert theme.surface, f"{name} missing surface"
            assert theme.text, f"{name} missing text"

    def test_theme_colors_are_hex(self):
        for name, theme in THEMES.items():
            assert theme.primary.startswith("#"), f"{name} primary not hex"
            assert theme.background.startswith("#"), f"{name} background not hex"
