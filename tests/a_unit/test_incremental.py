"""Tests for incremental list helper functions."""

from __future__ import annotations

from prezo.app import count_list_items, filter_list_items


class TestCountListItems:
    """Tests for count_list_items function."""

    def test_no_list_items(self):
        """Test content with no list items."""
        content = "# Title\n\nJust some text."
        assert count_list_items(content) == 0

    def test_single_unordered_item(self):
        """Test single unordered list item."""
        content = "# Title\n\n- Item 1"
        assert count_list_items(content) == 1

    def test_multiple_unordered_items(self):
        """Test multiple unordered list items."""
        content = "# Title\n\n- Item 1\n- Item 2\n- Item 3"
        assert count_list_items(content) == 3

    def test_ordered_list(self):
        """Test ordered list items."""
        content = "# Title\n\n1. First\n2. Second\n3. Third"
        assert count_list_items(content) == 3

    def test_mixed_markers(self):
        """Test different list markers."""
        content = "- Dash\n* Star\n+ Plus"
        assert count_list_items(content) == 3

    def test_ignores_nested_items(self):
        """Test that nested items are not counted."""
        content = "- Parent\n  - Child 1\n  - Child 2\n- Another parent"
        assert count_list_items(content) == 2

    def test_list_with_content_between(self):
        """Test list with other content between items."""
        content = "- Item 1\n\nSome paragraph.\n\n- Item 2"
        assert count_list_items(content) == 2

    def test_deeply_nested_list(self):
        """Test deeply nested list only counts top level."""
        content = "- Level 0\n  - Level 1\n    - Level 2\n- Another Level 0"
        assert count_list_items(content) == 2


class TestFilterListItems:
    """Tests for filter_list_items function."""

    def test_negative_max_shows_all(self):
        """Test that negative max_items shows all content."""
        content = "- Item 1\n- Item 2\n- Item 3"
        result = filter_list_items(content, -1)
        assert result == content

    def test_zero_items_shows_none(self):
        """Test that max_items=0 hides all list items."""
        content = "# Title\n\n- Item 1\n- Item 2"
        result = filter_list_items(content, 0)
        assert "- Item 1" not in result
        assert "- Item 2" not in result
        assert "# Title" in result

    def test_show_first_item(self):
        """Test showing only first item."""
        content = "- Item 1\n- Item 2\n- Item 3"
        result = filter_list_items(content, 1)
        assert "- Item 1" in result
        assert "- Item 2" not in result
        assert "- Item 3" not in result

    def test_show_first_two_items(self):
        """Test showing first two items."""
        content = "- Item 1\n- Item 2\n- Item 3"
        result = filter_list_items(content, 2)
        assert "- Item 1" in result
        assert "- Item 2" in result
        assert "- Item 3" not in result

    def test_max_greater_than_count(self):
        """Test max_items greater than actual count shows all."""
        content = "- Item 1\n- Item 2"
        result = filter_list_items(content, 10)
        assert "- Item 1" in result
        assert "- Item 2" in result

    def test_preserves_nested_items(self):
        """Test that nested items under visible parent are shown."""
        content = "- Parent\n  - Child 1\n  - Child 2\n- Hidden"
        result = filter_list_items(content, 1)
        assert "- Parent" in result
        assert "- Child 1" in result
        assert "- Child 2" in result
        assert "- Hidden" not in result

    def test_hides_nested_items_with_parent(self):
        """Test that nested items are hidden with their parent."""
        content = "- Visible\n- Parent\n  - Child\n- Also visible"
        result = filter_list_items(content, 2)
        assert "- Visible" in result
        assert "- Parent" in result
        assert "- Child" in result
        assert "- Also visible" not in result

    def test_preserves_non_list_content(self):
        """Test that non-list content is preserved."""
        content = "# Title\n\nParagraph\n\n- Item 1\n- Item 2"
        result = filter_list_items(content, 1)
        assert "# Title" in result
        assert "Paragraph" in result
        assert "- Item 1" in result
        assert "- Item 2" not in result

    def test_ordered_list_filtering(self):
        """Test filtering works with ordered lists."""
        content = "1. First\n2. Second\n3. Third"
        result = filter_list_items(content, 2)
        assert "1. First" in result
        assert "2. Second" in result
        assert "3. Third" not in result

    def test_empty_content(self):
        """Test empty content."""
        result = filter_list_items("", 5)
        assert result == ""

    def test_no_list_items(self):
        """Test content without list items."""
        content = "# Just a title\n\nSome text."
        result = filter_list_items(content, 1)
        assert result == content

    def test_preserves_layout_markers(self):
        """Test that layout markers (:::) are preserved."""
        content = """::: columns
::: column
- Item 1
- Item 2
:::
::: column
- Item 3
- Item 4
:::
:::"""
        result = filter_list_items(content, 2)
        # Should show first 2 items, hide last 2, but preserve all ::: markers
        assert "- Item 1" in result
        assert "- Item 2" in result
        assert "- Item 3" not in result
        assert "- Item 4" not in result
        # All layout markers should be preserved
        assert result.count(":::") == 6

    def test_layout_markers_reset_hidden_state(self):
        """Test that entering a new block resets hidden state for non-list content."""
        content = """::: columns
::: column
- Item 1
Some text after item
:::
::: column
More text here
- Item 2
:::
:::"""
        result = filter_list_items(content, 1)
        # First item shown, text after it shown (continuation)
        assert "- Item 1" in result
        assert "Some text after item" in result
        # Second column: text before item should be shown (new block)
        assert "More text here" in result
        # Second item hidden
        assert "- Item 2" not in result

    def test_maintains_line_count(self):
        """Test that hidden items are replaced with placeholders to maintain height."""
        content = "- Item 1\n- Item 2\n- Item 3"
        result = filter_list_items(content, 1)
        # Same number of lines
        assert result.count("\n") == content.count("\n")
        # First item visible, others are placeholders
        assert "- Item 1" in result
        assert "Item 2" not in result
        assert "Item 3" not in result

    def test_box_maintains_height(self):
        """Test that box content maintains height when filtering."""
        content = """::: box "My Box"
- First item
- Second item
- Third item
:::"""
        result = filter_list_items(content, 1)
        # Same number of lines (height preserved)
        assert result.count("\n") == content.count("\n")
        # Box markers preserved
        assert '::: box "My Box"' in result
        assert result.count(":::") == 2
        # First item visible
        assert "- First item" in result
        # Others hidden but lines preserved
        assert "- Second item" not in result
        assert "- Third item" not in result
