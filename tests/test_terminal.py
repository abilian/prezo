"""Tests for the terminal capability detection module."""

from __future__ import annotations

import os
from unittest import mock

from prezo.terminal import (
    ImageCapability,
    detect_image_capability,
    get_capability_summary,
    get_terminal_size,
    supports_true_color,
    supports_unicode,
)


class TestImageCapability:
    def test_enum_values(self):
        assert ImageCapability.KITTY.value == "kitty"
        assert ImageCapability.SIXEL.value == "sixel"
        assert ImageCapability.ITERM.value == "iterm"
        assert ImageCapability.ASCII.value == "ascii"
        assert ImageCapability.NONE.value == "none"


class TestDetectImageCapability:
    def test_detects_kitty_by_window_id(self):
        detect_image_capability.cache_clear()
        with mock.patch.dict(os.environ, {"KITTY_WINDOW_ID": "1"}, clear=True):
            result = detect_image_capability()
            assert result == ImageCapability.KITTY

    def test_detects_kitty_by_term(self):
        detect_image_capability.cache_clear()
        with mock.patch.dict(os.environ, {"TERM": "xterm-kitty"}, clear=True):
            result = detect_image_capability()
            assert result == ImageCapability.KITTY

    def test_detects_iterm_by_term_program(self):
        detect_image_capability.cache_clear()
        with mock.patch.dict(os.environ, {"TERM_PROGRAM": "iTerm.app"}, clear=True):
            result = detect_image_capability()
            assert result == ImageCapability.ITERM

    def test_detects_iterm_by_session_id(self):
        detect_image_capability.cache_clear()
        env = {"ITERM_SESSION_ID": "session123"}
        with mock.patch.dict(os.environ, env, clear=True):
            result = detect_image_capability()
            assert result == ImageCapability.ITERM

    def test_detects_sixel_by_term(self):
        detect_image_capability.cache_clear()
        with mock.patch.dict(os.environ, {"TERM": "mlterm"}, clear=True):
            result = detect_image_capability()
            assert result == ImageCapability.SIXEL

    def test_fallback_to_ascii(self):
        detect_image_capability.cache_clear()
        with mock.patch.dict(os.environ, {"TERM": "dumb"}, clear=True):
            result = detect_image_capability()
            assert result == ImageCapability.ASCII


class TestGetTerminalSize:
    def test_returns_tuple(self):
        cols, rows = get_terminal_size()
        assert isinstance(cols, int)
        assert isinstance(rows, int)
        assert cols > 0
        assert rows > 0

    def test_fallback_on_error(self):
        with mock.patch("os.get_terminal_size", side_effect=OSError):
            cols, rows = get_terminal_size()
            assert cols == 80
            assert rows == 24


class TestSupportsUnicode:
    def test_supports_utf8_encoding(self):
        with mock.patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = "utf-8"
            with mock.patch.dict(os.environ, {}, clear=True):
                assert supports_unicode() is True

    def test_supports_utf8_in_lang(self):
        with mock.patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = "ascii"
            with mock.patch.dict(os.environ, {"LANG": "en_US.UTF-8"}, clear=True):
                assert supports_unicode() is True

    def test_no_unicode_support(self):
        with mock.patch("sys.stdout") as mock_stdout:
            mock_stdout.encoding = "ascii"
            with mock.patch.dict(os.environ, {"LANG": "C"}, clear=True):
                assert supports_unicode() is False


class TestSupportsTrueColor:
    def test_supports_truecolor_env(self):
        with mock.patch.dict(os.environ, {"COLORTERM": "truecolor"}, clear=True):
            assert supports_true_color() is True

    def test_supports_24bit_env(self):
        with mock.patch.dict(os.environ, {"COLORTERM": "24bit"}, clear=True):
            assert supports_true_color() is True

    def test_supports_256color_term(self):
        with mock.patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True):
            assert supports_true_color() is True

    def test_supports_truecolor_in_iterm(self):
        with mock.patch.dict(os.environ, {"TERM_PROGRAM": "iTerm.app"}, clear=True):
            assert supports_true_color() is True

    def test_no_truecolor_support(self):
        with mock.patch.dict(os.environ, {"TERM": "dumb", "COLORTERM": ""}, clear=True):
            assert supports_true_color() is False


class TestGetCapabilitySummary:
    def test_returns_dict_with_expected_keys(self):
        detect_image_capability.cache_clear()
        summary = get_capability_summary()

        assert "image_capability" in summary
        assert "unicode" in summary
        assert "true_color" in summary
        assert "columns" in summary
        assert "rows" in summary
        assert "term" in summary
        assert "term_program" in summary

    def test_image_capability_is_string(self):
        detect_image_capability.cache_clear()
        summary = get_capability_summary()
        assert isinstance(summary["image_capability"], str)
