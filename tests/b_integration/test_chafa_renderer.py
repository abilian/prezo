"""Tests for chafa image renderer."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from prezo.images.chafa import ChafaRenderer, chafa_available, render_with_chafa


class TestChafaAvailable:
    """Tests for chafa_available function."""

    @patch("shutil.which")
    def test_returns_true_when_chafa_exists(self, mock_which):
        mock_which.return_value = "/usr/bin/chafa"
        assert chafa_available() is True
        mock_which.assert_called_with("chafa")

    @patch("shutil.which")
    def test_returns_false_when_chafa_missing(self, mock_which):
        mock_which.return_value = None
        assert chafa_available() is False


class TestRenderWithChafa:
    """Tests for render_with_chafa function."""

    @patch("prezo.images.chafa.chafa_available")
    def test_returns_none_when_chafa_unavailable(self, mock_available, tmp_path):
        mock_available.return_value = False
        path = tmp_path / "test.png"
        path.write_bytes(b"fake")
        result = render_with_chafa(path, 40, 20)
        assert result is None

    def test_returns_none_for_nonexistent_file(self, tmp_path):
        fake_path = tmp_path / "nonexistent.png"
        result = render_with_chafa(fake_path, 40, 20)
        assert result is None

    @pytest.fixture
    def real_image(self, tmp_path):
        """Create a real test image."""
        try:
            from PIL import Image

            img = Image.new("RGB", (100, 100), color="red")
            path = tmp_path / "test.png"
            img.save(path)
            return path
        except ImportError:
            pytest.skip("PIL not available")

    @pytest.mark.skipif(not chafa_available(), reason="chafa not installed")
    def test_renders_real_image_when_chafa_available(self, real_image):
        result = render_with_chafa(real_image, 40, 20)
        assert result is not None
        assert len(result) > 0

    @patch("subprocess.run")
    @patch("prezo.images.chafa.chafa_available")
    def test_calls_chafa_with_correct_args(self, mock_available, mock_run, tmp_path):
        mock_available.return_value = True
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "rendered output"

        path = tmp_path / "test.png"
        path.write_bytes(b"fake image data")

        render_with_chafa(path, 40, 20)

        # Verify chafa was called with expected arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        # First arg is the chafa executable (could be full path or just "chafa")
        assert call_args[0].endswith("chafa")
        assert "--size" in call_args
        assert "40x20" in call_args
        assert "--format" in call_args
        assert "symbols" in call_args

    @patch("subprocess.run")
    @patch("prezo.images.chafa.chafa_available")
    def test_returns_none_on_chafa_error(self, mock_available, mock_run, tmp_path):
        mock_available.return_value = True
        mock_run.return_value.returncode = 1

        path = tmp_path / "test.png"
        path.write_bytes(b"fake")

        result = render_with_chafa(path, 40, 20)
        assert result is None

    @patch("subprocess.run")
    @patch("prezo.images.chafa.chafa_available")
    def test_handles_timeout_exception(self, mock_available, mock_run, tmp_path):
        import subprocess

        mock_available.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="chafa", timeout=10)

        path = tmp_path / "test.png"
        path.write_bytes(b"fake")

        result = render_with_chafa(path, 40, 20)
        assert result is None


class TestChafaRenderer:
    """Tests for ChafaRenderer class."""

    def test_name_property(self):
        renderer = ChafaRenderer()
        assert renderer.name == "chafa"

    def test_supports_inline(self):
        renderer = ChafaRenderer()
        assert renderer.supports_inline() is True

    @patch("prezo.images.chafa.chafa_available")
    def test_available_property(self, mock_available):
        mock_available.return_value = True
        renderer = ChafaRenderer()
        assert renderer.available is True

    @patch("prezo.images.chafa.chafa_available")
    def test_not_available_property(self, mock_available):
        mock_available.return_value = False
        renderer = ChafaRenderer()
        assert renderer.available is False

    def test_render_placeholder_for_missing_file(self, tmp_path):
        renderer = ChafaRenderer()
        result = renderer._render_placeholder(tmp_path / "missing.png", 40, 10)

        assert "┌" in result
        assert "[Image:" in result
        assert "missing.png" in result

    def test_placeholder_truncates_long_name(self, tmp_path):
        renderer = ChafaRenderer()
        long_name = "a" * 100 + ".png"
        result = renderer._render_placeholder(tmp_path / long_name, 30, 10)

        assert "..." in result

    @pytest.fixture
    def test_image(self, tmp_path):
        """Create a test image."""
        try:
            from PIL import Image

            img = Image.new("RGB", (50, 50), color="green")
            path = tmp_path / "chafa_test.png"
            img.save(path)
            return path
        except ImportError:
            pytest.skip("PIL not available")

    @patch("prezo.images.chafa.render_with_chafa")
    def test_render_uses_chafa_when_available(self, mock_render, test_image):
        mock_render.return_value = "chafa output"
        renderer = ChafaRenderer()

        result = renderer.render(test_image, 40, 20)

        assert result == "chafa output"
        mock_render.assert_called_once_with(test_image, 40, 20)

    @patch("prezo.images.chafa.render_with_chafa")
    def test_render_falls_back_to_placeholder(self, mock_render, test_image):
        mock_render.return_value = None
        renderer = ChafaRenderer()

        result = renderer.render(test_image, 40, 20)

        # Should show placeholder
        assert "┌" in result
        assert "[Image:" in result
