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

    def test_wide_characters_cjk(self):
        # CJK characters take 2 cells each
        assert _visible_length("日本語") == 6  # 3 chars × 2 cells
        assert _visible_length("中文") == 4  # 2 chars × 2 cells
        assert _visible_length("한글") == 4  # 2 chars × 2 cells

    def test_wide_characters_emoji(self):
        # Emoji typically takes 2 cells
        assert _visible_length("👍") == 2
        assert _visible_length("Hello 👋") == 8  # 6 + 2

    def test_mixed_width_characters(self):
        # Mix of regular and wide characters
        assert _visible_length("AB日本CD") == 8  # 2 + 4 + 2


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


# =============================================================================
# Tests for new layout block types: right, spacer, box, divider
# =============================================================================


class TestParseRightBlock:
    """Tests for ::: right block parsing."""

    def test_simple_right(self):
        content = """::: right
Right-aligned text
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "right"
        assert "Right-aligned text" in blocks[0].content

    def test_right_with_markdown(self):
        content = """::: right
**Attribution**

— Author Name
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "right"
        assert "**Attribution**" in blocks[0].content


class TestParseSpacerBlock:
    """Tests for ::: spacer block parsing."""

    def test_simple_spacer(self):
        content = """::: spacer
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "spacer"
        # Default is 1 line
        assert blocks[0].width_percent == 1

    def test_spacer_with_count(self):
        content = """::: spacer 3
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "spacer"
        assert blocks[0].width_percent == 3

    def test_spacer_with_large_count(self):
        content = """::: spacer 10
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].width_percent == 10


class TestParseBoxBlock:
    """Tests for ::: box block parsing."""

    def test_simple_box(self):
        content = """::: box
Content in a box
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "box"
        assert "Content in a box" in blocks[0].content
        assert blocks[0].title == ""

    def test_box_with_quoted_title(self):
        content = """::: box "My Title"
Content here
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "box"
        assert blocks[0].title == "My Title"
        assert "Content here" in blocks[0].content

    def test_box_with_unquoted_title(self):
        content = """::: box Features
- Feature 1
- Feature 2
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "box"
        assert blocks[0].title == "Features"

    def test_box_with_markdown_content(self):
        content = """::: box "Important"
## Header

- Bullet 1
- Bullet 2

**Bold text**
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "box"
        assert "## Header" in blocks[0].content
        assert "**Bold text**" in blocks[0].content


class TestParseDividerBlock:
    """Tests for ::: divider block parsing."""

    def test_simple_divider(self):
        content = """::: divider
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "divider"
        assert blocks[0].style == "single"

    def test_divider_single(self):
        content = """::: divider single
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].style == "single"

    def test_divider_double(self):
        content = """::: divider double
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].style == "double"

    def test_divider_thick(self):
        content = """::: divider thick
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].style == "thick"

    def test_divider_dashed(self):
        content = """::: divider dashed
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].style == "dashed"


class TestRenderNewBlocks:
    """Tests for rendering new block types."""

    def test_render_right(self):
        blocks = [LayoutBlock(type="right", content="Right text")]
        renderable = render_layout(blocks)
        assert renderable is not None

    def test_render_spacer(self):
        blocks = [LayoutBlock(type="spacer", width_percent=2)]
        renderable = render_layout(blocks)
        assert renderable is not None

    def test_render_box(self):
        blocks = [LayoutBlock(type="box", content="Box content", title="Title")]
        renderable = render_layout(blocks)
        assert renderable is not None

    def test_render_box_no_title(self):
        blocks = [LayoutBlock(type="box", content="Box content")]
        renderable = render_layout(blocks)
        assert renderable is not None

    def test_render_divider(self):
        blocks = [LayoutBlock(type="divider", style="single")]
        renderable = render_layout(blocks)
        assert renderable is not None

    def test_render_divider_styles(self):
        for style in ["single", "double", "thick", "dashed"]:
            blocks = [LayoutBlock(type="divider", style=style)]
            renderable = render_layout(blocks)
            assert renderable is not None


class TestNewRenderables:
    """Tests for new renderable classes."""

    def test_right_renderable(self):
        from prezo.layout import RightRenderable

        renderer = RightRenderable("Right content")
        assert renderer.content == "Right content"

    def test_spacer_renderable_default(self):
        from prezo.layout import SpacerRenderable

        renderer = SpacerRenderable()
        assert renderer.lines == 1

    def test_spacer_renderable_custom(self):
        from prezo.layout import SpacerRenderable

        renderer = SpacerRenderable(5)
        assert renderer.lines == 5

    def test_spacer_renderable_minimum(self):
        from prezo.layout import SpacerRenderable

        renderer = SpacerRenderable(0)
        assert renderer.lines == 1  # Minimum is 1

        renderer = SpacerRenderable(-5)
        assert renderer.lines == 1  # Negative becomes 1

    def test_box_renderable(self):
        from prezo.layout import BoxRenderable

        renderer = BoxRenderable("Content", "Title")
        assert renderer.content == "Content"
        assert renderer.title == "Title"

    def test_box_renderable_no_title(self):
        from prezo.layout import BoxRenderable

        renderer = BoxRenderable("Content")
        assert renderer.content == "Content"
        assert renderer.title == ""

    def test_divider_renderable_default(self):
        from prezo.layout import DividerRenderable

        renderer = DividerRenderable()
        assert renderer.style == "single"

    def test_divider_renderable_styles(self):
        from prezo.layout import DividerRenderable

        for style in ["single", "double", "thick", "dashed"]:
            renderer = DividerRenderable(style)
            assert renderer.style == style

    def test_divider_renderable_invalid_style(self):
        from prezo.layout import DividerRenderable

        renderer = DividerRenderable("invalid")
        assert renderer.style == "single"  # Falls back to default


class TestMixedNewBlocks:
    """Tests for mixing new block types with existing ones."""

    def test_columns_with_divider(self):
        content = """::: columns
::: column
Left
:::
::: column
Right
:::
:::

::: divider
:::

More content"""
        blocks = parse_layout(content)

        assert len(blocks) == 3
        assert blocks[0].type == "columns"
        assert blocks[1].type == "divider"
        assert blocks[2].type == "plain"

    def test_box_in_sequence(self):
        content = """Introduction

::: box "Features"
- Feature 1
- Feature 2
:::

::: spacer 2
:::

::: box "Benefits"
- Benefit 1
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 4
        assert blocks[0].type == "plain"
        assert blocks[1].type == "box"
        assert blocks[1].title == "Features"
        assert blocks[2].type == "spacer"
        assert blocks[3].type == "box"

    def test_right_attribution(self):
        content = """::: center
# Quote

"The best way to predict the future is to invent it."
:::

::: right
— Alan Kay
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 2
        assert blocks[0].type == "center"
        assert blocks[1].type == "right"
        assert "Alan Kay" in blocks[1].content


class TestLayoutBlockExtendedDataclass:
    """Tests for extended LayoutBlock fields."""

    def test_title_field(self):
        block = LayoutBlock(type="box", title="My Title")
        assert block.title == "My Title"

    def test_style_field(self):
        block = LayoutBlock(type="divider", style="double")
        assert block.style == "double"

    def test_default_title(self):
        block = LayoutBlock(type="box")
        assert block.title == ""

    def test_default_style(self):
        block = LayoutBlock(type="divider")
        assert block.style == ""


class TestNestedLayoutBlocks:
    """Tests for nested layout blocks within columns."""

    def test_box_inside_column(self):
        """Test that box blocks inside columns are parsed correctly."""
        content = """::: columns
::: column
::: box "Title"
Content
:::
:::
::: column
Other content
:::
:::"""
        blocks = parse_layout(content)

        assert len(blocks) == 1
        assert blocks[0].type == "columns"
        # The column content contains the raw box syntax
        col1_content = blocks[0].children[0].content
        assert "::: box" in col1_content

    def test_nested_blocks_render(self):
        """Test that nested layout blocks render without error."""
        from rich.console import Console

        from prezo.layout import ColumnsRenderable

        # Column with nested box
        columns = [
            LayoutBlock(
                type="column",
                content="""::: box "Features"
- Item 1
- Item 2
:::""",
            ),
            LayoutBlock(type="column", content="Plain content"),
        ]
        renderer = ColumnsRenderable(columns, gap=2)

        # Should render without error
        console = Console(width=80, force_terminal=True)
        # Consume the generator to trigger rendering
        list(renderer.__rich_console__(console, console.options))

    def test_divider_inside_column(self):
        """Test divider inside column renders correctly."""
        from rich.console import Console

        from prezo.layout import ColumnsRenderable

        columns = [
            LayoutBlock(
                type="column",
                content="""Header

::: divider
:::

Footer""",
            ),
        ]
        renderer = ColumnsRenderable(columns, gap=2)
        console = Console(width=40, force_terminal=True)
        list(renderer.__rich_console__(console, console.options))

    def test_multiple_nested_blocks(self):
        """Test multiple nested blocks in a column."""
        from rich.console import Console

        from prezo.layout import ColumnsRenderable

        columns = [
            LayoutBlock(
                type="column",
                content="""::: box "Box 1"
Content 1
:::

::: spacer
:::

::: box "Box 2"
Content 2
:::""",
            ),
        ]
        renderer = ColumnsRenderable(columns, gap=2)
        console = Console(width=60, force_terminal=True)
        list(renderer.__rich_console__(console, console.options))
