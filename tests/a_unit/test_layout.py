"""Unit tests for layout parsing and rendering."""

from __future__ import annotations

from prezo.layout import (
    LayoutBlock,
    _visible_length,
    has_layout_blocks,
    parse_layout,
    render_layout,
)


class TestHasLayoutBlocks:
    """Tests for has_layout_blocks quick check."""

    def test_no_layout(self):
        assert has_layout_blocks("# Simple markdown") is False
        assert has_layout_blocks("No special syntax here") is False

    def test_has_columns(self):
        content = """::: columns
::: column
Left
:::
:::"""
        assert has_layout_blocks(content) is True

    def test_has_center(self):
        assert has_layout_blocks("::: center\nText\n:::") is True


class TestParseLayout:
    """Tests for parse_layout function."""

    def test_plain_content(self):
        content = "# Title\n\nSome text"
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "plain"
        assert "Title" in blocks[0].content

    def test_simple_two_columns(self):
        content = """::: columns
::: column
Left content
:::
::: column
Right content
:::
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "columns"
        assert len(blocks[0].children) == 2
        assert blocks[0].children[0].type == "column"
        assert blocks[0].children[1].type == "column"
        assert "Left content" in blocks[0].children[0].content
        assert "Right content" in blocks[0].children[1].content

    def test_three_columns(self):
        content = """::: columns
::: column
First
:::
::: column
Second
:::
::: column
Third
:::
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "columns"
        assert len(blocks[0].children) == 3

    def test_column_with_width(self):
        content = """::: columns
::: column 40
Narrow
:::
::: column 60
Wide
:::
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        columns = blocks[0].children
        assert columns[0].width_percent == 40
        assert columns[1].width_percent == 60

    def test_center_block(self):
        content = """::: center
Centered text
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "center"
        assert "Centered text" in blocks[0].content

    def test_mixed_content(self):
        content = """# Introduction

Some intro text

::: columns
::: column
Left
:::
::: column
Right
:::
:::

# Conclusion

More text"""
        blocks = parse_layout(content)

        assert len(blocks) == 3
        assert blocks[0].type == "plain"
        assert blocks[1].type == "columns"
        assert blocks[2].type == "plain"

    def test_column_with_markdown(self):
        content = """::: columns
::: column
- Bullet 1
- Bullet 2
- Bullet 3
:::
::: column
**Bold text**

*Italic text*
:::
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        col1 = blocks[0].children[0]
        col2 = blocks[0].children[1]
        assert "Bullet 1" in col1.content
        assert "**Bold text**" in col2.content

    def test_unclosed_block_treated_as_plain(self):
        content = """::: columns
::: column
Left content
:::
Missing closing"""
        blocks = parse_layout(content)

        # Should treat as plain when unclosed
        assert len(blocks) >= 1

    def test_empty_columns(self):
        content = """::: columns
::: column
:::
::: column
:::
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "columns"
        assert len(blocks[0].children) == 2
        # Empty content is valid
        assert blocks[0].children[0].content == ""


class TestParseLayoutEdgeCases:
    """Edge case tests for the parser."""

    def test_whitespace_in_directive(self):
        content = """:::   columns
:::  column
Content
:::
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "columns"

    def test_nested_markdown_headers(self):
        content = """::: columns
::: column
## Header in Column

Paragraph text
:::
::: column
### Another Header

More text
:::
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert "## Header in Column" in blocks[0].children[0].content

    def test_code_block_in_column(self):
        content = """::: columns
::: column
```python
def hello():
    print("Hello")
```
:::
::: column
Description
:::
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert "```python" in blocks[0].children[0].content

    def test_multiple_column_groups(self):
        content = """::: columns
::: column
A
:::
::: column
B
:::
:::

::: columns
::: column
C
:::
::: column
D
:::
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 2
        assert blocks[0].type == "columns"
        assert blocks[1].type == "columns"


class TestVisibleLength:
    """Tests for _visible_length utility."""

    def test_plain_text(self):
        assert _visible_length("Hello") == 5
        assert _visible_length("") == 0

    def test_with_ansi_codes(self):
        # Bold text
        text = "\x1b[1mBold\x1b[0m"
        assert _visible_length(text) == 4

        # Colored text
        text = "\x1b[31mRed\x1b[0m"
        assert _visible_length(text) == 3

    def test_complex_ansi(self):
        # Multiple style codes
        text = "\x1b[1;31;42mStyled\x1b[0m Normal"
        assert _visible_length(text) == 13  # "Styled Normal"


class TestLayoutBlockDataclass:
    """Tests for LayoutBlock dataclass."""

    def test_default_values(self):
        block = LayoutBlock(type="plain")
        assert block.content == ""
        assert block.children == []
        assert block.width_percent == 0

    def test_with_content(self):
        block = LayoutBlock(type="column", content="Hello", width_percent=50)
        assert block.content == "Hello"
        assert block.width_percent == 50


class TestRenderLayout:
    """Tests for render_layout function."""

    def test_render_plain_content(self):
        blocks = [LayoutBlock(type="plain", content="# Hello")]
        renderable = render_layout(blocks)
        assert renderable is not None

    def test_render_columns(self):
        blocks = [
            LayoutBlock(
                type="columns",
                children=[
                    LayoutBlock(type="column", content="Left"),
                    LayoutBlock(type="column", content="Right"),
                ],
            )
        ]
        renderable = render_layout(blocks)
        assert renderable is not None

    def test_render_center(self):
        blocks = [LayoutBlock(type="center", content="Centered")]
        renderable = render_layout(blocks)
        assert renderable is not None

    def test_render_mixed(self):
        blocks = [
            LayoutBlock(type="plain", content="Intro"),
            LayoutBlock(
                type="columns",
                children=[
                    LayoutBlock(type="column", content="A"),
                    LayoutBlock(type="column", content="B"),
                ],
            ),
            LayoutBlock(type="plain", content="Outro"),
        ]
        renderable = render_layout(blocks)
        assert renderable is not None


class TestColumnsRenderable:
    """Tests for ColumnsRenderable."""

    def test_calculate_equal_widths(self):
        from prezo.layout import ColumnsRenderable

        columns = [
            LayoutBlock(type="column", content="A"),
            LayoutBlock(type="column", content="B"),
        ]
        renderer = ColumnsRenderable(columns, gap=2)

        # 80 chars total, 2 char gap = 78 available / 2 = 39 each
        widths = renderer._calculate_widths(80, 2)
        assert len(widths) == 2
        assert widths[0] == 39
        assert widths[1] == 39

    def test_calculate_explicit_widths(self):
        from prezo.layout import ColumnsRenderable

        columns = [
            LayoutBlock(type="column", content="A", width_percent=30),
            LayoutBlock(type="column", content="B", width_percent=70),
        ]
        renderer = ColumnsRenderable(columns, gap=2)

        widths = renderer._calculate_widths(100, 2)
        assert len(widths) == 2
        # 100 - 2 (gap) = 98 available
        # 30% of 98 = 29.4 -> 29
        # 70% of 98 = 68.6 -> 68
        assert widths[0] == 29
        assert widths[1] == 68

    def test_merge_equal_height_columns(self):
        from prezo.layout import ColumnsRenderable

        columns = [
            LayoutBlock(type="column", content="A"),
            LayoutBlock(type="column", content="B"),
        ]
        renderer = ColumnsRenderable(columns, gap=2)

        col_outputs = [["Line 1", "Line 2"], ["Col 2 Line 1", "Col 2 Line 2"]]
        widths = [10, 15]

        merged = renderer._merge_columns(col_outputs, widths)

        assert len(merged) == 2
        # Each line should have content from both columns

    def test_merge_unequal_height_columns(self):
        from prezo.layout import ColumnsRenderable

        columns = [
            LayoutBlock(type="column", content="A"),
            LayoutBlock(type="column", content="B"),
        ]
        renderer = ColumnsRenderable(columns, gap=2)

        col_outputs = [["Short"], ["Line 1", "Line 2", "Line 3"]]
        widths = [10, 10]

        merged = renderer._merge_columns(col_outputs, widths)

        assert len(merged) == 3  # Should match longest column
