"""Tests for prezo widgets."""

from __future__ import annotations

from prezo.widgets import SlideButton
from prezo.widgets.slide_button import extract_slide_title


class TestExtractSlideTitle:
    """Tests for extract_slide_title function."""

    def test_extracts_h1(self):
        content = "# First Slide\n\nSome content"
        title = extract_slide_title(content, 0)
        assert title == "First Slide"

    def test_extracts_h2(self):
        content = "## Second Level Heading\n\nContent"
        title = extract_slide_title(content, 0)
        assert title == "Second Level Heading"

    def test_extracts_h3(self):
        content = "### Third Level\n\nContent"
        title = extract_slide_title(content, 0)
        assert title == "Third Level"

    def test_extracts_h6(self):
        content = "###### Smallest Heading\n\nContent"
        title = extract_slide_title(content, 0)
        assert title == "Smallest Heading"

    def test_removes_bold_markers(self):
        content = "# **Bold Title**\n\nContent"
        title = extract_slide_title(content, 0)
        assert title == "Bold Title"
        assert "**" not in title

    def test_removes_italic_markers(self):
        content = "# *Italic Title*\n\nContent"
        title = extract_slide_title(content, 0)
        assert title == "Italic Title"
        assert "*" not in title

    def test_truncates_long_titles(self):
        content = (
            "# This is a very long title that should be truncated "
            "because it exceeds the maximum length\n\nContent"
        )
        title = extract_slide_title(content, 0)
        assert len(title) <= 35
        assert title.endswith("...")

    def test_fallback_to_first_line(self):
        content = "No heading here\n\nJust plain text"
        title = extract_slide_title(content, 0)
        assert title == "No heading here"

    def test_fallback_truncates_long_line(self):
        content = (
            "This is a very long first line without any heading "
            "that should be truncated\n\nMore content"
        )
        title = extract_slide_title(content, 0)
        assert len(title) <= 35
        assert title.endswith("...")

    def test_fallback_to_slide_number(self):
        content = ""
        title = extract_slide_title(content, 0)
        assert title == "Slide 1"

        title = extract_slide_title(content, 4)
        assert title == "Slide 5"

    def test_skips_html_comments(self):
        content = "<!-- comment -->\n# Real Title\n\nContent"
        title = extract_slide_title(content, 0)
        assert title == "Real Title"

    def test_skips_empty_lines(self):
        content = "\n\n# Title After Blanks\n\nContent"
        title = extract_slide_title(content, 0)
        assert title == "Title After Blanks"

    def test_whitespace_only_content(self):
        content = "   \n  \n   "
        title = extract_slide_title(content, 2)
        assert title == "Slide 3"

    def test_heading_with_extra_whitespace(self):
        content = "#   Spaced   Title   \n\nContent"
        title = extract_slide_title(content, 0)
        assert "Spaced" in title


class TestSlideButtonCreation:
    """Tests for SlideButton widget creation."""

    def test_button_has_correct_id(self):
        button = SlideButton(5, "# Test", is_current=False)
        assert button.id == "slide-5"

    def test_button_stores_slide_index(self):
        button = SlideButton(3, "# Test", is_current=False)
        assert button.slide_index == 3

    def test_button_stores_is_current(self):
        button = SlideButton(0, "# Test", is_current=True)
        assert button.is_current is True

        button2 = SlideButton(1, "# Test", is_current=False)
        assert button2.is_current is False
