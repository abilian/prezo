"""Tests for the presentation parser."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prezo.parser import (
    Presentation,
    PresentationConfig,
    Slide,
    clean_marp_directives,
    extract_images,
    extract_notes,
    extract_prezo_directives,
    extract_slide_incremental,
    parse_presentation,
    split_slides,
)


class TestSlide:
    """Tests for the Slide dataclass."""

    def test_slide_creation(self):
        slide = Slide(content="# Hello", index=0)
        assert slide.content == "# Hello"
        assert slide.index == 0
        assert slide.raw_content == ""
        assert slide.notes == ""

    def test_slide_with_notes(self):
        slide = Slide(
            content="# Hello",
            index=1,
            raw_content="# Hello\n???Notes",
            notes="Notes",
        )
        assert slide.notes == "Notes"


class TestPresentation:
    """Tests for the Presentation dataclass."""

    def test_empty_presentation(self):
        pres = Presentation()
        assert pres.total_slides == 0
        assert pres.title == ""
        assert pres.theme == "default"

    def test_total_slides(self):
        slides = [Slide(content=f"Slide {i}", index=i) for i in range(5)]
        pres = Presentation(slides=slides)
        assert pres.total_slides == 5


class TestSplitSlides:
    """Tests for split_slides function."""

    def test_single_slide(self):
        content = "# Single Slide\n\nContent here."
        slides = split_slides(content)
        assert len(slides) == 1
        assert "# Single Slide" in slides[0]

    def test_multiple_slides(self):
        content = "# Slide 1\n\n---\n\n# Slide 2\n\n---\n\n# Slide 3"
        slides = split_slides(content)
        assert len(slides) == 3
        assert "# Slide 1" in slides[0]
        assert "# Slide 2" in slides[1]
        assert "# Slide 3" in slides[2]

    def test_empty_content(self):
        slides = split_slides("")
        assert len(slides) == 1
        assert slides[0] == ""

    def test_separator_with_whitespace(self):
        content = "# Slide 1\n\n---  \n\n# Slide 2"
        slides = split_slides(content)
        assert len(slides) == 2


class TestExtractNotes:
    """Tests for extract_notes function."""

    def test_no_notes(self):
        content = "# Slide\n\nJust content."
        slide_content, notes = extract_notes(content)
        assert slide_content == content
        assert notes == ""

    def test_question_mark_notes(self):
        content = "# Slide\n\nContent\n???\nThese are my notes"
        slide_content, notes = extract_notes(content)
        assert "# Slide" in slide_content
        assert "Content" in slide_content
        assert "???" not in slide_content
        assert "These are my notes" in notes

    def test_html_comment_notes(self):
        content = "# Slide\n\n<!-- notes: Speaker notes here -->\n\nMore content"
        slide_content, notes = extract_notes(content)
        assert "Speaker notes here" in notes
        assert "<!-- notes" not in slide_content

    def test_html_comment_notes_multiline(self):
        content = "# Slide\n\n<!-- notes:\nLine 1\nLine 2\n-->\n\nContent"
        _slide_content, notes = extract_notes(content)
        assert "Line 1" in notes
        assert "Line 2" in notes


class TestCleanMarpDirectives:
    """Tests for clean_marp_directives function."""

    def test_removes_class_directive(self):
        content = "<!-- _class: lead -->\n# Title"
        cleaned = clean_marp_directives(content)
        assert "<!-- _class" not in cleaned
        assert "# Title" in cleaned

    def test_removes_bg_image(self):
        content = "# Title\n\n![bg right](image.png)\n\nContent"
        cleaned = clean_marp_directives(content)
        assert "![bg" not in cleaned
        assert "# Title" in cleaned
        assert "Content" in cleaned

    def test_keeps_regular_images(self):
        content = "# Title\n\n![Regular image](photo.jpg)\n\nContent"
        cleaned = clean_marp_directives(content)
        assert "![Regular image]" in cleaned

    def test_removes_empty_divs(self):
        content = '# Title\n\n<div style="color: red;"></div>\n\nContent'
        cleaned = clean_marp_directives(content)
        assert "<div" not in cleaned

    def test_unwraps_content_divs(self):
        content = '<div class="columns">\n- Item 1\n- Item 2\n</div>'
        cleaned = clean_marp_directives(content)
        assert "- Item 1" in cleaned
        assert "- Item 2" in cleaned
        assert "<div" not in cleaned
        assert "</div>" not in cleaned

    def test_collapses_multiple_blank_lines(self):
        content = "# Title\n\n\n\n\n\nContent"
        cleaned = clean_marp_directives(content)
        assert "\n\n\n" not in cleaned


class TestParsePresentation:
    """Tests for parse_presentation function."""

    def test_parse_from_string(self, sample_presentation_md):
        pres = parse_presentation(sample_presentation_md)
        assert pres.title == "Test Presentation"
        assert pres.theme == "default"
        assert pres.total_slides == 3
        assert pres.source_path is None

    def test_parse_from_file(self, sample_presentation_md):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(sample_presentation_md)
            f.flush()
            path = Path(f.name)

        try:
            pres = parse_presentation(path)
            assert pres.title == "Test Presentation"
            assert pres.source_path == path
        finally:
            path.unlink()

    def test_parse_marp_header_as_title(self, marp_presentation_md):
        pres = parse_presentation(marp_presentation_md)
        assert pres.title == "MARP Header Title"

    def test_parse_cleans_marp_directives(self, marp_presentation_md):
        pres = parse_presentation(marp_presentation_md)
        first_slide = pres.slides[0].content
        assert "<!-- _class" not in first_slide
        assert "![bg" not in first_slide

    def test_parse_extracts_notes(self, sample_presentation_md):
        pres = parse_presentation(sample_presentation_md)
        third_slide = pres.slides[2]
        assert "presenter notes" in third_slide.notes

    def test_parse_preserves_raw_content(self, sample_presentation_md):
        pres = parse_presentation(sample_presentation_md)
        for slide in pres.slides:
            assert slide.raw_content != ""

    def test_parse_simple_no_frontmatter(self, simple_presentation_md):
        pres = parse_presentation(simple_presentation_md)
        assert pres.title == ""
        assert pres.total_slides == 1
        assert "# Only Slide" in pres.slides[0].content


class TestPresentationUpdateSlide:
    """Tests for Presentation.update_slide method."""

    def test_update_slide_no_source(self, sample_presentation_md):
        pres = parse_presentation(sample_presentation_md)
        # source_path is None when parsed from string
        with pytest.raises(ValueError, match="no source file path"):
            pres.update_slide(0, "New content")

    def test_update_slide_invalid_index(self, sample_presentation_md):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(sample_presentation_md)
            f.flush()
            path = Path(f.name)

        try:
            pres = parse_presentation(path)
            with pytest.raises(ValueError, match="Invalid slide index"):
                pres.update_slide(99, "New content")
        finally:
            path.unlink()

    def test_update_slide_saves_to_file(self, sample_presentation_md):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(sample_presentation_md)
            f.flush()
            path = Path(f.name)

        try:
            pres = parse_presentation(path)
            pres.update_slide(0, "# Updated First Slide\n\nNew content here.")

            # Read back the file
            new_content = path.read_text()
            assert "# Updated First Slide" in new_content
            assert "New content here." in new_content

            # Re-parse and verify
            pres2 = parse_presentation(path)
            assert "Updated First Slide" in pres2.slides[0].content
        finally:
            path.unlink()


class TestPresentationConfig:
    """Tests for PresentationConfig dataclass."""

    def test_default_values(self):
        config = PresentationConfig()
        assert config.theme is None
        assert config.show_clock is None
        assert config.show_elapsed is None
        assert config.countdown_minutes is None
        assert config.image_mode is None

    def test_merge_to_dict_empty(self):
        config = PresentationConfig()
        result = config.merge_to_dict()
        assert result == {}

    def test_merge_to_dict_with_values(self):
        config = PresentationConfig(
            theme="dark",
            show_clock=True,
            countdown_minutes=45,
        )
        result = config.merge_to_dict()
        assert result["display"]["theme"] == "dark"
        assert result["timer"]["show_clock"] is True
        assert result["timer"]["countdown_minutes"] == 45


class TestExtractprezoDirectives:
    """Tests for extract_prezo_directives function."""

    def test_no_directives(self):
        content = "# Just a slide\n\nSome content."
        config = extract_prezo_directives(content)
        assert config.theme is None
        assert config.show_clock is None

    def test_extract_theme(self):
        content = """<!-- prezo
theme: dracula
-->

# Slide Title
"""
        config = extract_prezo_directives(content)
        assert config.theme == "dracula"

    def test_extract_multiple_directives(self):
        content = """<!-- prezo
theme: dark
show_clock: true
show_elapsed: false
countdown_minutes: 30
image_mode: ascii
-->

# Slide Content
"""
        config = extract_prezo_directives(content)
        assert config.theme == "dark"
        assert config.show_clock is True
        assert config.show_elapsed is False
        assert config.countdown_minutes == 30
        assert config.image_mode == "ascii"

    def test_boolean_variations(self):
        content = """<!-- prezo
show_clock: yes
show_elapsed: 1
-->
"""
        config = extract_prezo_directives(content)
        assert config.show_clock is True
        assert config.show_elapsed is True

    def test_invalid_countdown_ignored(self):
        content = """<!-- prezo
countdown_minutes: invalid
-->
"""
        config = extract_prezo_directives(content)
        assert config.countdown_minutes is None

    def test_case_insensitive_keys(self):
        content = """<!-- prezo
THEME: light
ShowClock: true
-->
"""
        config = extract_prezo_directives(content)
        assert config.theme == "light"
        assert config.show_clock is True


class TestPresentationWithDirectives:
    """Tests for parsing presentations with prezo directives."""

    def test_directives_parsed_into_presentation(self):
        md = """---
title: Test
---

<!-- prezo
theme: nord
countdown_minutes: 45
-->

# First Slide
"""
        pres = parse_presentation(md)
        assert pres.directives.theme == "nord"
        assert pres.directives.countdown_minutes == 45

    def test_directives_override_frontmatter_theme(self):
        md = """---
title: Test
theme: default
---

<!-- prezo
theme: dracula
-->

# Slide
"""
        pres = parse_presentation(md)
        # Directive theme should override frontmatter
        assert pres.theme == "dracula"


class TestExtractImages:
    """Tests for extract_images function."""

    def test_no_images(self):
        content = "# Just text\n\nNo images here."
        images = extract_images(content)
        assert images == []

    def test_single_image(self):
        content = "# Slide\n\n![Alt text](image.png)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].alt == "Alt text"
        assert images[0].path == "image.png"

    def test_multiple_images(self):
        content = "![First](a.png)\n\nText\n\n![Second](b.jpg)"
        images = extract_images(content)
        assert len(images) == 2
        assert images[0].alt == "First"
        assert images[1].alt == "Second"

    def test_image_positions(self):
        content = "# Title\n\n![Test](pic.png)\n\nMore text"
        images = extract_images(content)
        assert len(images) == 1
        # Verify start/end positions
        assert content[images[0].start : images[0].end] == "![Test](pic.png)"

    def test_extracts_marp_background(self):
        """MARP bg images are now extracted with layout info."""
        content = "![bg](background.jpg)\n\n![regular](image.png)"
        images = extract_images(content)
        assert len(images) == 2
        # Background image
        assert images[0].path == "background.jpg"
        assert images[0].layout == "background"
        # Regular image
        assert images[1].path == "image.png"
        assert images[1].layout == "inline"

    def test_extracts_marp_bg_with_options(self):
        """MARP bg images with options are extracted with layout info."""
        content = "![bg left:40%](bg.jpg)\n![normal](pic.png)"
        images = extract_images(content)
        assert len(images) == 2
        # Left layout image with size
        assert images[0].path == "bg.jpg"
        assert images[0].layout == "left"
        assert images[0].size_percent == 40
        # Regular image
        assert images[1].path == "pic.png"
        assert images[1].layout == "inline"

    def test_marp_right_layout(self):
        """Test MARP right layout directive."""
        content = "![bg right](side.jpg)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].layout == "right"
        assert images[0].size_percent == 50  # Default

    def test_marp_right_with_size(self):
        """Test MARP right layout with custom size."""
        content = "![bg right:30%](side.jpg)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].layout == "right"
        assert images[0].size_percent == 30

    def test_marp_fit_layout(self):
        """Test MARP fit directive."""
        content = "![bg fit](full.jpg)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].layout == "fit"

    def test_image_with_empty_alt(self):
        content = "![](no-alt.png)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].alt == ""
        assert images[0].path == "no-alt.png"

    def test_image_with_path_containing_spaces(self):
        content = "![Photo](my image.png)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].path == "my image.png"


class TestMarpImageDirectives:
    """Tests for MARP image directive parsing."""

    def test_bg_only_is_background_layout(self):
        content = "![bg](image.png)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].layout == "background"
        assert images[0].size_percent == 100

    def test_bg_left_default_size(self):
        content = "![bg left](image.png)"
        images = extract_images(content)
        assert images[0].layout == "left"
        assert images[0].size_percent == 50

    def test_bg_left_with_percentage(self):
        content = "![bg left:40%](image.png)"
        images = extract_images(content)
        assert images[0].layout == "left"
        assert images[0].size_percent == 40

    def test_bg_right_default_size(self):
        content = "![bg right](image.png)"
        images = extract_images(content)
        assert images[0].layout == "right"
        assert images[0].size_percent == 50

    def test_bg_right_with_percentage(self):
        content = "![bg right:60%](image.png)"
        images = extract_images(content)
        assert images[0].layout == "right"
        assert images[0].size_percent == 60

    def test_bg_fit_layout(self):
        content = "![bg fit](image.png)"
        images = extract_images(content)
        assert images[0].layout == "fit"
        assert images[0].size_percent == 100

    def test_bg_contain_is_fit(self):
        content = "![bg contain](image.png)"
        images = extract_images(content)
        assert images[0].layout == "fit"

    def test_bg_cover_is_background(self):
        content = "![bg cover](image.png)"
        images = extract_images(content)
        assert images[0].layout == "background"

    def test_regular_image_is_inline(self):
        content = "![alt text](image.png)"
        images = extract_images(content)
        assert images[0].layout == "inline"
        assert images[0].size_percent == 50

    def test_bg_with_uppercase(self):
        """Test case insensitivity of bg directive."""
        content = "![BG LEFT](image.png)"
        images = extract_images(content)
        assert images[0].layout == "left"

    def test_bg_with_extra_text_in_alt(self):
        """Test that extra text after directive is cleaned as alt."""
        content = "![bg left:30% My Photo](image.png)"
        images = extract_images(content)
        assert images[0].layout == "left"
        assert images[0].size_percent == 30
        assert images[0].alt == "My Photo"

    def test_unknown_bg_directive_is_background(self):
        """Unknown bg directives default to background."""
        content = "![bg something](image.png)"
        images = extract_images(content)
        assert images[0].layout == "background"

    def test_mixed_images_in_slide(self):
        """Test slide with both bg and regular images."""
        content = "![bg left](side.png)\n\n![Photo](inline.png)"
        images = extract_images(content)
        assert len(images) == 2
        assert images[0].layout == "left"
        assert images[1].layout == "inline"


class TestSlideWithImages:
    """Tests for Slide dataclass with images."""

    def test_slide_has_images_field(self):
        slide = Slide(content="# Hello", index=0)
        assert slide.images == []

    def test_parsed_slide_extracts_images(self):
        md = """# Slide with Image

![My Image](test.png)

Some text after.
"""
        pres = parse_presentation(md)
        assert len(pres.slides) == 1
        assert len(pres.slides[0].images) == 1
        assert pres.slides[0].images[0].alt == "My Image"
        assert pres.slides[0].images[0].path == "test.png"


class TestMarpSizeDirectives:
    """Tests for MARP image size directives (width/height)."""

    def test_width_directive_short_form(self):
        """Test w:N shorthand for width."""
        content = "![w:50](image.png)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].width == 50
        assert images[0].height is None

    def test_width_directive_long_form(self):
        """Test width:N full form."""
        content = "![width:80](image.png)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].width == 80

    def test_height_directive_short_form(self):
        """Test h:N shorthand for height."""
        content = "![h:20](image.png)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].height == 20
        assert images[0].width is None

    def test_height_directive_long_form(self):
        """Test height:N full form."""
        content = "![height:30](image.png)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].height == 30

    def test_width_and_height_combined(self):
        """Test both width and height in same image."""
        content = "![w:60 h:40](image.png)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].width == 60
        assert images[0].height == 40

    def test_size_with_alt_text(self):
        """Test size directives with alt text."""
        content = "![w:50 h:30 My Photo](image.png)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].width == 50
        assert images[0].height == 30
        assert images[0].alt == "My Photo"

    def test_bg_with_size_directives(self):
        """Test bg layout combined with size directives."""
        content = "![bg left w:40 h:25](image.png)"
        images = extract_images(content)
        assert len(images) == 1
        assert images[0].layout == "left"
        assert images[0].width == 40
        assert images[0].height == 25

    def test_size_cleans_from_alt(self):
        """Test that size directives are removed from alt text."""
        content = "![Photo w:50](image.png)"
        images = extract_images(content)
        assert images[0].alt == "Photo"
        assert "w:" not in images[0].alt

    def test_inline_image_with_size(self):
        """Test inline image with size remains inline layout."""
        content = "![w:40](image.png)"
        images = extract_images(content)
        assert images[0].layout == "inline"
        assert images[0].width == 40

    def test_no_size_directives(self):
        """Test image without size directives has None values."""
        content = "![Regular image](image.png)"
        images = extract_images(content)
        assert images[0].width is None
        assert images[0].height is None


class TestExtractSlideIncremental:
    """Tests for extract_slide_incremental function."""

    def test_no_directive_returns_none(self):
        """Test that no directive returns None."""
        content = "# Slide\n\n- Item 1\n- Item 2"
        result = extract_slide_incremental(content)
        assert result is None

    def test_incremental_directive_returns_true(self):
        """Test that <!-- incremental --> returns True."""
        content = "# Slide\n\n<!-- incremental -->\n\n- Item 1\n- Item 2"
        result = extract_slide_incremental(content)
        assert result is True

    def test_no_incremental_directive_returns_false(self):
        """Test that <!-- no-incremental --> returns False."""
        content = "# Slide\n\n<!-- no-incremental -->\n\n- Item 1\n- Item 2"
        result = extract_slide_incremental(content)
        assert result is False

    def test_case_insensitive(self):
        """Test that directives are case insensitive."""
        content = "# Slide\n\n<!-- INCREMENTAL -->\n\n- Item 1"
        result = extract_slide_incremental(content)
        assert result is True

    def test_directive_with_extra_whitespace(self):
        """Test directive with extra whitespace."""
        content = "# Slide\n\n<!--   incremental   -->\n\n- Item 1"
        result = extract_slide_incremental(content)
        assert result is True


class TestSlideIncremental:
    """Tests for Slide.incremental field."""

    def test_slide_has_incremental_field(self):
        """Test that Slide has incremental field."""
        slide = Slide(content="# Hello", index=0)
        assert slide.incremental is None

    def test_slide_with_incremental_set(self):
        """Test Slide with incremental set."""
        slide = Slide(content="# Hello", index=0, incremental=True)
        assert slide.incremental is True

    def test_parsed_slide_extracts_incremental(self):
        """Test that parsed slide extracts incremental directive."""
        md = """# Slide

<!-- incremental -->

- Item 1
- Item 2
"""
        pres = parse_presentation(md)
        assert len(pres.slides) == 1
        assert pres.slides[0].incremental is True

    def test_parsed_slide_extracts_no_incremental(self):
        """Test that parsed slide extracts no-incremental directive."""
        md = """# Slide

<!-- no-incremental -->

- Item 1
- Item 2
"""
        pres = parse_presentation(md)
        assert pres.slides[0].incremental is False


class TestIncrementalListsDirective:
    """Tests for incremental_lists in PresentationConfig."""

    def test_default_value_is_none(self):
        """Test that default value is None."""
        config = PresentationConfig()
        assert config.incremental_lists is None

    def test_extract_from_prezo_block(self):
        """Test extracting incremental_lists from prezo block."""
        content = """<!-- prezo
incremental_lists: true
-->

# Slide
"""
        config = extract_prezo_directives(content)
        assert config.incremental_lists is True

    def test_extract_false_value(self):
        """Test extracting false value."""
        content = """<!-- prezo
incremental_lists: false
-->

# Slide
"""
        config = extract_prezo_directives(content)
        assert config.incremental_lists is False

    def test_alternative_key_names(self):
        """Test alternative key names like incremental."""
        content = """<!-- prezo
incremental: yes
-->
"""
        config = extract_prezo_directives(content)
        assert config.incremental_lists is True

    def test_merge_to_dict_includes_incremental(self):
        """Test that merge_to_dict includes incremental_lists."""
        config = PresentationConfig(incremental_lists=True)
        result = config.merge_to_dict()
        assert result["behavior"]["incremental_lists"] is True
