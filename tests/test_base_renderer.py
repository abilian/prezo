"""Tests for base image renderer module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from prezo.images.base import NullRenderer, get_renderer
from prezo.terminal import ImageCapability


class TestNullRenderer:
    """Tests for NullRenderer class."""

    def test_name_property(self):
        renderer = NullRenderer()
        assert renderer.name == "none"

    def test_supports_inline_returns_false(self):
        renderer = NullRenderer()
        assert renderer.supports_inline() is False

    def test_render_returns_empty_string(self, tmp_path):
        renderer = NullRenderer()
        fake_path = tmp_path / "any.png"
        result = renderer.render(fake_path, 100, 50)
        assert result == ""


class TestGetRenderer:
    """Tests for get_renderer factory function."""

    def test_none_mode_returns_null_renderer(self):
        renderer = get_renderer("none")
        assert isinstance(renderer, NullRenderer)

    def test_ascii_mode_returns_ascii_renderer(self):
        renderer = get_renderer("ascii")
        assert renderer.name == "ascii"

    @patch("prezo.images.base.detect_image_capability")
    def test_auto_mode_uses_detection(self, mock_detect):
        mock_detect.return_value = ImageCapability.ASCII
        renderer = get_renderer("auto")
        assert renderer.name == "ascii"
        mock_detect.assert_called_once()

    @patch("prezo.images.base.detect_image_capability")
    def test_auto_mode_kitty_detection(self, mock_detect):
        mock_detect.return_value = ImageCapability.KITTY
        renderer = get_renderer("auto")
        assert renderer.name == "kitty"

    @patch("prezo.images.base.detect_image_capability")
    def test_auto_mode_iterm_detection(self, mock_detect):
        mock_detect.return_value = ImageCapability.ITERM
        renderer = get_renderer("auto")
        assert renderer.name == "iterm"

    @patch("prezo.images.base.detect_image_capability")
    def test_auto_mode_sixel_detection(self, mock_detect):
        mock_detect.return_value = ImageCapability.SIXEL
        renderer = get_renderer("auto")
        assert renderer.name == "sixel"

    def test_explicit_kitty_mode(self):
        renderer = get_renderer("kitty")
        assert renderer.name == "kitty"

    def test_explicit_iterm_mode(self):
        renderer = get_renderer("iterm")
        assert renderer.name == "iterm"

    def test_explicit_sixel_mode(self):
        renderer = get_renderer("sixel")
        assert renderer.name == "sixel"

    def test_unknown_mode_defaults_to_ascii(self):
        renderer = get_renderer("unknown_mode")
        assert renderer.name == "ascii"

    @patch("prezo.images.base.get_config")
    def test_none_mode_uses_config(self, mock_config):
        mock_config.return_value.images.mode = "ascii"
        renderer = get_renderer(None)
        assert renderer.name == "ascii"

    @patch("prezo.images.base.get_config")
    def test_none_mode_with_config_none(self, mock_config):
        mock_config.return_value.images.mode = "none"
        renderer = get_renderer(None)
        assert isinstance(renderer, NullRenderer)


class TestRendererProtocol:
    """Tests to verify renderers satisfy the ImageRenderer protocol."""

    @pytest.fixture(params=["ascii", "kitty", "iterm", "sixel", "none"])
    def renderer(self, request):
        """Get renderer for each mode."""
        return get_renderer(request.param)

    def test_has_render_method(self, renderer):
        assert hasattr(renderer, "render")
        assert callable(renderer.render)

    def test_has_supports_inline_method(self, renderer):
        assert hasattr(renderer, "supports_inline")
        assert callable(renderer.supports_inline)

    def test_has_name_property(self, renderer):
        assert hasattr(renderer, "name")
        assert isinstance(renderer.name, str)

    def test_render_returns_string(self, renderer, tmp_path):
        fake_path = tmp_path / "test.png"
        fake_path.write_bytes(b"fake")
        result = renderer.render(fake_path, 20, 10)
        assert isinstance(result, str)

    def test_supports_inline_returns_bool(self, renderer):
        result = renderer.supports_inline()
        assert isinstance(result, bool)
