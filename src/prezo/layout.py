"""Layout parsing and rendering for multi-column slides.

Supports Pandoc-style fenced div syntax:

    ::: columns
    ::: column
    Left content
    :::
    ::: column
    Right content
    :::
    :::

Additional layout blocks:
    ::: center          - Horizontally centered content
    ::: right           - Right-aligned content
    ::: spacer [n]      - Vertical space (default 1 line)
    ::: box [title]     - Bordered panel with optional title
    ::: divider [style] - Horizontal rule (single/double/thick/dashed)

"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import StringIO
from typing import TYPE_CHECKING, Literal

import rich.box
from rich.cells import cell_len
from rich.console import (
    Console,
    ConsoleOptions,
    Group,
    RenderResult,
)
from rich.markdown import Markdown
from rich.measure import Measurement
from rich.panel import Panel
from rich.rule import Rule
from rich.segment import Segment
from rich.style import Style
from rich.text import Text

from prezo.emoji import MARKER_STYLES

if TYPE_CHECKING:
    from rich.console import RenderableType

# -----------------------------------------------------------------------------
# Styled Markdown Rendering
# -----------------------------------------------------------------------------

# Patterns for detecting h1/h2 headings
_H1_PATTERN = re.compile(r"^#\s+(.+)$")
_H2_PATTERN = re.compile(r"^##\s+(.+)$")


class _HangingIndentText:
    """A renderable that displays text with hanging indentation.

    First line has a prefix (like "• "), continuation lines are indented
    to align with the text after the prefix.
    """

    def __init__(self, prefix: str, text: str, base_style: str) -> None:
        self.prefix = prefix
        self.text = text
        self.base_style = base_style

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render text with hanging indentation."""
        max_width = options.max_width
        prefix_width = cell_len(self.prefix)

        # Calculate available width for text
        text_width = max_width - prefix_width
        if text_width < 10:
            text_width = max_width  # Fallback if too narrow

        # Pre-render the full text with inline formatting so styles (bold,
        # italic, code, links) span correctly across line wraps. Rich's
        # Text.wrap is style-aware and preserves styling across breaks.
        formatted = _render_text_with_formatting(self.text, self.base_style)
        lines = formatted.wrap(console, text_width)

        # Build output with hanging indent
        indent = " " * prefix_width
        for i, line in enumerate(lines):
            result = Text(style=self.base_style)
            result.append(self.prefix if i == 0 else indent)
            result.append_text(line)
            yield result

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        """Return the measurement of this renderable."""
        return Measurement(len(self.prefix) + 1, options.max_width)


# Patterns for bullet and numbered lists
_BULLET_LIST_PATTERN = re.compile(r"^(\s*)([-*+])\s+(.*)$")
_NUMBERED_LIST_PATTERN = re.compile(r"^(\s*)(\d+\.)\s+(.*)$")


_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _render_text_with_formatting(
    text: str,
    base_style: str,
) -> Text:
    """Render text with inline formatting like **bold**, *italic*, and [links](url).

    Args:
        text: Text with possible markdown formatting.
        base_style: Base style string (e.g., "#e0e0e0 on #1e1e1e").

    Returns:
        Rich Text object with appropriate styling.

    """
    result = Text(style=base_style)
    i = 0
    while i < len(text):
        # Check for markdown links [text](url)
        if text[i] == "[":
            match = _LINK_PATTERN.match(text, i)
            if match:
                link_text = match.group(1)
                link_url = match.group(2)
                # Use Rich's link style for OSC 8 clickable links
                result.append(link_text, style=f"underline cyan link {link_url}")
                i = match.end()
                continue
        # Check for **bold**
        if text[i : i + 2] == "**":
            end = text.find("**", i + 2)
            if end != -1:
                result.append(text[i + 2 : end], style=f"bold {base_style}")
                i = end + 2
                continue
        # Check for *italic* (but not **)
        if text[i] == "*" and (i + 1 >= len(text) or text[i + 1] != "*"):
            end = text.find("*", i + 1)
            if end != -1 and (end + 1 >= len(text) or text[end + 1] != "*"):
                result.append(text[i + 1 : end], style=f"italic {base_style}")
                i = end + 1
                continue
        # Check for `code`
        if text[i] == "`":
            end = text.find("`", i + 1)
            if end != -1:
                result.append(text[i + 1 : end], style=f"bold cyan {base_style}")
                i = end + 1
                continue
        # Regular character
        result.append(text[i])
        i += 1
    return result


class _MarkdownRenderer:
    """Helper class for rendering styled markdown content."""

    def __init__(
        self,
        primary_color: str,
        text_color: str,
        surface_color: str,
    ) -> None:
        self.primary_color = primary_color
        self.text_color = text_color
        self.surface_color = surface_color
        self.base_style = f"{text_color} on {surface_color}"
        self.renderables: list[RenderableType] = []
        self.current_block: list[str] = []
        self.in_list = False
        self.in_code_fence = False

    def flush_block(self) -> None:
        """Flush accumulated lines as regular markdown."""
        if self.current_block:
            block_text = "\n".join(self.current_block).strip()
            if block_text:
                self.renderables.append(Markdown(block_text, style=self.base_style))
            self.current_block.clear()
        self.in_list = False

    def end_list(self) -> None:
        """End current list block with spacing."""
        if self.in_list:
            self.renderables.append(Text("", style=self.base_style))
            self.in_list = False

    def render_list_item(self, indent: str, marker: str, text: str) -> None:
        """Render a list item with proper styling and hanging indent."""
        if not self.in_list:
            self.renderables.append(Text("", style=self.base_style))
            self.in_list = True

        indent_level = len(indent) // 2 if indent else 0
        visual_indent = "  " * indent_level
        bullet = "•" if marker in "-*+" else marker
        prefix = f"{visual_indent}{bullet} "
        self.renderables.append(_HangingIndentText(prefix, text, self.base_style))

    def render_h1(self, title: str) -> None:
        """Render an H1 heading."""
        self.flush_block()
        self.renderables.append(Text("", style=self.base_style))
        title_text = _render_text_with_formatting(title, f"bold {self.text_color}")
        title_text.justify = "center"
        panel = Panel(
            title_text,
            border_style=self.primary_color,
            box=rich.box.HEAVY,
            padding=(0, 2),
            style=self.base_style,
        )
        self.renderables.append(panel)
        self.renderables.append(Text("", style=self.base_style))

    def render_h2(self, title: str) -> None:
        """Render an H2 heading."""
        self.flush_block()
        self.renderables.append(Text("", style=self.base_style))
        h2_style = f"bold {self.primary_color} on {self.surface_color}"
        title_text = _render_text_with_formatting(title, h2_style)
        title_text.justify = "center"
        self.renderables.append(title_text)
        self.renderables.append(Text("", style=self.base_style))

    def _process_list_match(self, indent: str, marker: str, text: str) -> None:
        """Process a matched list item (bullet or numbered)."""
        if not self.in_list:
            self.flush_block()
        self.render_list_item(indent, marker, text)

    def process_line(self, line: str) -> None:
        """Process a single line of markdown."""
        # Track fenced code blocks - lines inside them are passed through raw
        if line.startswith("```"):
            self.in_code_fence = not self.in_code_fence
        if self.in_code_fence or line.startswith("```"):
            self.current_block.append(line)
            return

        # Check for headings
        h1_match = _H1_PATTERN.match(line)
        if h1_match:
            self.render_h1(h1_match.group(1).strip())
            return

        h2_match = _H2_PATTERN.match(line)
        if h2_match:
            self.render_h2(h2_match.group(1).strip())
            return

        # Check for list items
        bullet_match = _BULLET_LIST_PATTERN.match(line)
        if bullet_match:
            self._process_list_match(
                bullet_match.group(1), bullet_match.group(2), bullet_match.group(3)
            )
            return

        numbered_match = _NUMBERED_LIST_PATTERN.match(line)
        if numbered_match:
            self._process_list_match(
                numbered_match.group(1),
                numbered_match.group(2),
                numbered_match.group(3),
            )
            return

        # Handle list termination
        if self.in_list:
            if not line.strip():
                return  # Empty line in a list - skip it
            self.end_list()

        # Regular content
        self.current_block.append(line)

    def render(self, content: str) -> RenderableType:
        """Render the full content and return a Rich renderable."""
        for line in content.split("\n"):
            self.process_line(line)

        self.end_list()
        self.flush_block()

        if len(self.renderables) == 0:
            return Text("")
        if len(self.renderables) == 1:
            return self.renderables[0]
        return Group(*self.renderables)


def render_styled_markdown(
    content: str,
    primary_color: str = "#0178d4",
    text_color: str = "#e0e0e0",
    surface_color: str = "#1e1e1e",
) -> RenderableType:
    """Render markdown with styled headings.

    H1: Centered bold text in a heavy-bordered panel
    H2: Centered bold text in primary color

    Args:
        content: Markdown content to render.
        primary_color: Theme primary color for borders and H2.
        text_color: Theme text color.
        surface_color: Theme surface/background color.

    Returns:
        Rich renderable for the styled content.

    """
    if not content.strip():
        return Text("")

    renderer = _MarkdownRenderer(primary_color, text_color, surface_color)
    return renderer.render(content)


# -----------------------------------------------------------------------------
# Data Types
# -----------------------------------------------------------------------------


BlockType = Literal[
    "plain", "columns", "column", "center", "right", "spacer", "box", "divider"
]


@dataclass
class LayoutBlock:
    """A block of content with layout information."""

    type: BlockType
    content: str = ""  # Raw markdown content (for leaf blocks)
    children: list[LayoutBlock] = field(default_factory=list)
    width_percent: int = 0  # For column blocks (0 = auto/equal)
    title: str = ""  # For box blocks
    style: str = ""  # For divider blocks (single/double/thick/dashed)


# -----------------------------------------------------------------------------
# Parser
# -----------------------------------------------------------------------------

# Pattern for opening fenced div: ::: type [arg]
# arg can be: a number (width %), a quoted string (title), or a word (style)
OPEN_PATTERN = re.compile(r'^:::\s*(\w+)(?:\s+"([^"]+)"|\s+(\S+))?\s*$')
# Pattern for closing fenced div: :::
CLOSE_PATTERN = re.compile(r"^:::\s*$")

# Block types that don't require content (self-closing)
SELF_CLOSING_TYPES = {"spacer", "divider"}


def parse_layout(content: str) -> list[LayoutBlock]:
    """Parse markdown content into layout blocks.

    Detects Pandoc-style fenced divs and builds a tree of LayoutBlocks.
    Content outside fenced divs becomes plain blocks.

    Args:
        content: Markdown content possibly containing fenced divs.

    Returns:
        List of LayoutBlock objects representing the content structure.

    """
    lines = content.split("\n")
    blocks: list[LayoutBlock] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        match = OPEN_PATTERN.match(line)

        if match:
            block_type = match.group(1).lower()
            # Group 2 is quoted string, Group 3 is unquoted arg
            quoted_arg = match.group(2)  # For "title"
            unquoted_arg = match.group(3)  # For width or style

            # Self-closing blocks (spacer, divider) don't need content or closing :::
            if block_type in SELF_CLOSING_TYPES:
                block = _create_block(block_type, "", quoted_arg, unquoted_arg)
                blocks.append(block)
                i = _skip_redundant_close(lines, i + 1)
                continue

            # Find matching close and nested content
            block, end_idx = _parse_fenced_block(
                lines, i, block_type, quoted_arg, unquoted_arg
            )
            if block:
                blocks.append(block)
                i = end_idx + 1
                continue
            # Unclosed block - treat as plain text, skip the opening line
            i += 1
            continue

        # Not a fenced div - accumulate plain content
        plain_lines = []
        while i < len(lines):
            if OPEN_PATTERN.match(lines[i]):
                break
            plain_lines.append(lines[i])
            i += 1

        if plain_lines:
            plain_content = "\n".join(plain_lines).strip()
            if plain_content:
                blocks.append(LayoutBlock(type="plain", content=plain_content))

    return blocks


def _skip_redundant_close(lines: list[str], start: int) -> int:
    """Skip a redundant closing ::: that follows a void directive.

    Void directives (spacer, divider) need no closing marker, but authors add
    one by analogy with container divs. Consume it (and any intervening blank
    lines) so it does not leak as literal text.

    Args:
        lines: All lines of content.
        start: Index just past the void directive.

    Returns:
        The index to resume parsing from.

    """
    j = start
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    if j < len(lines) and CLOSE_PATTERN.match(lines[j]):
        return j + 1
    return start


def _create_block(
    block_type: str,
    inner_content: str,
    quoted_arg: str | None,
    unquoted_arg: str | None,
) -> LayoutBlock:
    """Create a LayoutBlock from parsed fenced div content.

    Args:
        block_type: The type from ::: type.
        inner_content: Content inside the fenced div.
        quoted_arg: Quoted argument (e.g., title for box).
        unquoted_arg: Unquoted argument (e.g., width or style).

    Returns:
        A LayoutBlock of the appropriate type.

    """
    content = inner_content.strip()
    width = int(unquoted_arg) if unquoted_arg and unquoted_arg.isdigit() else 0

    # Use a dispatch table for simple content blocks
    simple_types = {"center", "right", "plain"}

    if block_type == "columns":
        block = LayoutBlock(type="columns")
        block.children = parse_layout(inner_content)
    elif block_type == "column":
        block = LayoutBlock(type="column", content=content, width_percent=width)
    elif block_type == "spacer":
        lines_count = width if width > 0 else 1
        block = LayoutBlock(type="spacer", width_percent=lines_count)
    elif block_type == "box":
        title = quoted_arg or unquoted_arg or ""
        block = LayoutBlock(type="box", content=content, title=title)
    elif block_type == "divider":
        style = unquoted_arg or "single"
        block = LayoutBlock(type="divider", style=style)
    elif block_type in simple_types:
        block = LayoutBlock(type=block_type, content=content)
    else:
        # Unknown block type - treat as plain
        block = LayoutBlock(type="plain", content=content)

    return block


def _parse_fenced_block(
    lines: list[str],
    start: int,
    block_type: str,
    quoted_arg: str | None,
    unquoted_arg: str | None,
) -> tuple[LayoutBlock | None, int]:
    """Parse a fenced div block starting at the given line.

    Args:
        lines: All lines of content.
        start: Starting line index (the opening :::).
        block_type: The type from ::: type.
        quoted_arg: Quoted argument (e.g., title for box).
        unquoted_arg: Unquoted argument (e.g., width or style).

    Returns:
        Tuple of (LayoutBlock or None, end line index).

    """
    depth = 1
    i = start + 1
    content_lines: list[str] = []

    while i < len(lines) and depth > 0:
        line = lines[i]

        if CLOSE_PATTERN.match(line):
            depth -= 1
            if depth == 0:
                break
            content_lines.append(line)
        elif OPEN_PATTERN.match(line):
            depth += 1
            content_lines.append(line)
        else:
            content_lines.append(line)
        i += 1

    if depth != 0:
        # Unclosed block - treat as plain text
        return None, start

    inner_content = "\n".join(content_lines)
    block = _create_block(block_type, inner_content, quoted_arg, unquoted_arg)
    return block, i


def has_layout_blocks(content: str) -> bool:
    """Check if content contains any layout directives.

    Quick check to avoid parsing overhead for simple slides.

    Args:
        content: Markdown content to check.

    Returns:
        True if content contains ::: directives.

    """
    return ":::" in content


# -----------------------------------------------------------------------------
# Renderer
# -----------------------------------------------------------------------------


class ColumnsRenderable:
    """Rich renderable that displays columns side-by-side."""

    def __init__(
        self,
        columns: list[LayoutBlock],
        gap: int = 2,
    ) -> None:
        """Initialize columns renderable.

        Args:
            columns: List of column LayoutBlocks.
            gap: Number of spaces between columns.

        """
        self.columns = columns
        self.gap = gap

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render columns side-by-side."""
        if not self.columns:
            return

        # Blank line before columns
        yield Text("")

        max_width = options.max_width
        num_cols = len(self.columns)

        # Calculate column widths
        widths = self._calculate_widths(max_width, num_cols)

        # Render each column to lines
        column_outputs: list[list[str]] = []
        for col, width in zip(self.columns, widths, strict=False):
            lines = self._render_column(col, width, console)
            column_outputs.append(lines)

        # Merge columns side-by-side
        merged = self._merge_columns(column_outputs, widths)

        for line in merged:
            yield Text.from_ansi(line)

        # Blank line after columns
        yield Text("")

    def _calculate_widths(self, total_width: int, num_cols: int) -> list[int]:
        """Calculate width for each column.

        Args:
            total_width: Total available width.
            num_cols: Number of columns.

        Returns:
            List of widths for each column.

        """
        # Account for gaps between columns
        total_gap = self.gap * (num_cols - 1)
        available = total_width - total_gap

        # Check if any columns have explicit widths
        explicit_widths = [c.width_percent for c in self.columns]
        total_explicit = sum(w for w in explicit_widths if w > 0)

        if total_explicit > 0:
            # Use explicit percentages
            widths = []
            remaining = available
            auto_count = sum(1 for w in explicit_widths if w == 0)

            for w in explicit_widths:
                if w > 0:
                    col_width = max(1, (available * w) // 100)
                    widths.append(col_width)
                    remaining -= col_width
                else:
                    widths.append(0)  # Placeholder

            # Distribute remaining to auto columns
            if auto_count > 0:
                auto_width = remaining // auto_count
                widths = [w if w > 0 else auto_width for w in widths]
        else:
            # Equal distribution
            col_width = available // num_cols
            widths = [col_width] * num_cols

        return widths

    def _render_column(
        self, column: LayoutBlock, width: int, console: Console
    ) -> list[str]:
        """Render a single column to a list of lines.

        Args:
            column: The column LayoutBlock.
            width: Width in characters.
            console: Rich console for rendering.

        Returns:
            List of rendered lines (with ANSI codes).

        """
        # Create a console with fixed width for rendering
        col_console = Console(
            width=width,
            force_terminal=True,
            color_system=console.color_system,
            record=True,
            file=StringIO(),
        )

        # Render content - check for nested layout blocks
        if column.content:
            if has_layout_blocks(column.content):
                # Parse and render nested layout blocks
                blocks = parse_layout(column.content)
                renderable = render_layout(blocks)
                col_console.print(renderable)
            else:
                # Plain markdown
                md = Markdown(column.content)
                col_console.print(md)

        # Get rendered lines
        output = col_console.export_text(styles=True)
        lines = output.split("\n")

        # Ensure each line is padded to column width
        # Note: This is tricky with ANSI codes. For now, we'll do basic padding.
        padded = []
        for line in lines:
            # Strip trailing whitespace but preserve ANSI
            stripped = line.rstrip()
            padded.append(stripped)

        return padded

    def _merge_columns(
        self, column_outputs: list[list[str]], widths: list[int]
    ) -> list[str]:
        """Merge column outputs side-by-side.

        Args:
            column_outputs: List of line lists for each column.
            widths: Width of each column.

        Returns:
            Merged lines.

        """
        if not column_outputs:
            return []

        # Find max height
        max_height = max(len(col) for col in column_outputs)

        # Pad shorter columns
        for col in column_outputs:
            while len(col) < max_height:
                col.append("")

        # Merge line by line
        result = []
        gap_str = " " * self.gap

        for row_idx in range(max_height):
            parts = []
            for col_idx, col in enumerate(column_outputs):
                line = col[row_idx] if row_idx < len(col) else ""
                # Pad to column width (accounting for ANSI codes)
                visible_len = _visible_length(line)
                padding = widths[col_idx] - visible_len
                if padding > 0:
                    line = line + " " * padding
                parts.append(line)

            result.append(gap_str.join(parts))

        return result

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        """Return the measurement of this renderable."""
        return Measurement(1, options.max_width)


class CenterRenderable:
    """Rich renderable that centers content horizontally."""

    def __init__(self, content: str) -> None:
        """Initialize center renderable.

        Args:
            content: Markdown content to center.

        """
        self.content = content

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render centered content."""
        # Blank line before centered content
        yield Text("")

        # Use Markdown with center justification
        md = Markdown(self.content, justify="center")
        yield md

        # Blank line after centered content
        yield Text("")

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        """Return the measurement of this renderable."""
        return Measurement(1, options.max_width)


class RightRenderable:
    """Rich renderable that right-aligns content."""

    def __init__(self, content: str) -> None:
        """Initialize right-align renderable.

        Args:
            content: Markdown content to right-align.

        """
        self.content = content

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render right-aligned content."""
        yield Text("")
        md = Markdown(self.content, justify="right")
        yield md
        yield Text("")

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        """Return the measurement of this renderable."""
        return Measurement(1, options.max_width)


class SpacerRenderable:
    """Rich renderable that creates vertical space."""

    def __init__(self, lines: int = 1) -> None:
        """Initialize spacer renderable.

        Args:
            lines: Number of blank lines to insert.

        """
        self.lines = max(1, lines)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render vertical space."""
        for _ in range(self.lines):
            yield Text("")

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        """Return the measurement of this renderable."""
        return Measurement(0, 0)


class BoxRenderable:
    """Rich renderable that displays content in a bordered panel."""

    def __init__(self, content: str, title: str = "") -> None:
        """Initialize box renderable.

        Args:
            content: Markdown content to display in the box.
            title: Optional title for the box.

        """
        self.content = content
        self.title = title

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render content in a bordered panel."""
        content = _render_box_content(self.content)
        panel = Panel(content, title=self.title or None)
        yield panel

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        """Return the measurement of this renderable."""
        return Measurement(1, options.max_width)


# Divider style characters
DIVIDER_STYLES = {
    "single": "─",
    "double": "═",
    "thick": "━",
    "dashed": "╌",
}


class DividerRenderable:
    """Rich renderable that displays a horizontal rule."""

    def __init__(self, style: str = "single") -> None:
        """Initialize divider renderable.

        Args:
            style: Style of the divider (single, double, thick, dashed).

        """
        self.style = style if style in DIVIDER_STYLES else "single"

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render horizontal rule."""
        yield Text("")
        char = DIVIDER_STYLES[self.style]
        yield Rule(characters=char)
        yield Text("")

    def __rich_measure__(
        self, console: Console, options: ConsoleOptions
    ) -> Measurement:
        """Return the measurement of this renderable."""
        return Measurement(1, options.max_width)


def _render_block(
    block: LayoutBlock,
    primary_color: str = "#0178d4",
    text_color: str = "#e0e0e0",
    surface_color: str = "#1e1e1e",
) -> list[RenderableType]:
    """Render a single block to Rich renderables.

    Args:
        block: A LayoutBlock to render.
        primary_color: Theme primary color for styled headings.
        text_color: Theme text color.
        surface_color: Theme surface/background color.

    Returns:
        List of Rich renderables for this block.

    """
    if block.type == "columns":
        result: list[RenderableType] = []
        columns = [c for c in block.children if c.type == "column"]
        if columns:
            result.append(ColumnsRenderable(columns))
        # Also render any non-column children (plain text between columns)
        for child in block.children:
            if child.type == "plain":
                result.append(
                    render_styled_markdown(
                        child.content, primary_color, text_color, surface_color
                    )
                )
        return result

    if block.type == "spacer":
        return [SpacerRenderable(block.width_percent)]

    if block.type == "box":
        return [BoxRenderable(block.content, block.title)]

    if block.type == "divider":
        return [DividerRenderable(block.style)]

    # Simple content blocks: plain, center, right, column
    renderable_map: dict[str, type] = {
        "center": CenterRenderable,
        "right": RightRenderable,
    }
    if block.type in renderable_map:
        return [renderable_map[block.type](block.content)]

    # Default: plain markdown with styled headings
    return [
        render_styled_markdown(block.content, primary_color, text_color, surface_color)
    ]


def render_layout(
    blocks: list[LayoutBlock],
    primary_color: str = "#0178d4",
    text_color: str = "#e0e0e0",
    surface_color: str = "#1e1e1e",
) -> RenderableType:
    """Render layout blocks to a Rich renderable.

    Args:
        blocks: List of LayoutBlocks from parse_layout().
        primary_color: Theme primary color for styled headings.
        text_color: Theme text color.
        surface_color: Theme surface/background color.

    Returns:
        Rich renderable representing the layout.

    """
    renderables: list[RenderableType] = []

    for block in blocks:
        renderables.extend(
            _render_block(block, primary_color, text_color, surface_color)
        )

    if len(renderables) == 1:
        return renderables[0]
    return Group(*renderables)


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

# Pattern for bullet list items
_BULLET_PATTERN = re.compile(r"^[-*+]\s+(.*)$")

# Pattern for numbered list items
_NUMBERED_PATTERN = re.compile(r"^(\d+\.)\s+(.*)$")


def _parse_inline_formatting(text: str) -> Text:
    """Parse inline markdown formatting: **bold**, *italic*, `code`, [links](url).

    Args:
        text: Text with possible markdown formatting markers.

    Returns:
        Rich Text object with appropriate styling.

    """
    return _render_text_with_formatting(text, "")


def _line_to_box_item(line: str) -> RenderableType | None:
    """Turn a single non-empty line of box content into a renderable.

    Returns a hanging-indent renderable for bullet/numbered list items,
    or None if the line is plain text (caller accumulates it).
    """
    bullet_match = _BULLET_PATTERN.match(line)
    if bullet_match:
        return _HangingIndentText("• ", bullet_match.group(1), "")

    numbered_match = _NUMBERED_PATTERN.match(line)
    if numbered_match:
        return _HangingIndentText(
            f"{numbered_match.group(1)} ", numbered_match.group(2), ""
        )
    return None


def _render_box_content(content: str) -> RenderableType:
    """Render box content with compact spacing and hanging indent on lists.

    List items use hanging indent so wrapped continuation lines align
    under the text rather than the bullet character.

    Args:
        content: Markdown content for the box.

    Returns:
        Rich renderable for the box content.

    """
    lines = [line.strip() for line in content.strip().split("\n")]
    if not lines:
        return Text()

    renderables: list[RenderableType] = []
    text_buffer = Text()

    def flush_text() -> None:
        nonlocal text_buffer
        if text_buffer.plain:
            renderables.append(text_buffer)
            text_buffer = Text()

    for stripped in lines:
        if not stripped:
            flush_text()
            renderables.append(Text(""))
            continue

        item = _line_to_box_item(stripped)
        if item is not None:
            flush_text()
            renderables.append(item)
            continue

        if text_buffer.plain:
            text_buffer.append("\n")
        text_buffer.append_text(_parse_inline_formatting(stripped))

    flush_text()

    if not renderables:
        return Text()
    if len(renderables) == 1:
        return renderables[0]
    return Group(*renderables)


# ANSI escape sequence pattern
_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def _visible_length(text: str) -> int:
    """Calculate visible cell width of text, excluding ANSI codes.

    Uses Rich's cell_len for proper Unicode width handling:
    - Regular ASCII characters = 1 cell
    - Wide characters (CJK, emoji) = 2 cells
    - Zero-width characters = 0 cells

    Args:
        text: Text possibly containing ANSI escape codes.

    Returns:
        Visible cell width (terminal columns).

    """
    # Strip ANSI codes first, then calculate cell width
    clean_text = _ANSI_PATTERN.sub("", text)

    # Strip OSC 8 hyperlink opening: \x1b]8;id=ID;URL\x1b\\
    clean_text = re.sub(r'\x1b\]8;id=[0-9]+;[^\x1b]*\x1b\\', '', clean_text)

    # Strip OSC 8 hyperlink closing: \x1b]8;;\x1b\\
    clean_text = re.sub(r'\x1b\]8;;\x1b\\', '', clean_text)

    return cell_len(clean_text)


# -----------------------------------------------------------------------------
# Emoji-marker colouring
# -----------------------------------------------------------------------------

# Matches any ASCII fallback marker (e.g. ``[V]``) produced by replace_emoji.
_MARKER_PATTERN = re.compile(
    "(" + "|".join(re.escape(marker) for marker in MARKER_STYLES) + ")"
)


class _MarkerColorizer:
    """Renderable wrapper that tints emoji-fallback markers after rendering.

    Operates on the final segment stream, so markers are coloured uniformly
    wherever they appear (paragraphs, list items, tables, box titles) without
    needing to understand Markdown structure.
    """

    def __init__(self, renderable: RenderableType) -> None:
        r"""Wrap a renderable so its ``[V]``, ``/!\``, … markers are coloured."""
        self.renderable = renderable

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Re-render the wrapped renderable, recolouring marker tokens."""
        for segment in console.render(self.renderable, options):
            yield from _recolor_segment(segment)


def _recolor_segment(segment: Segment) -> RenderResult:
    """Split a segment on markers, applying each marker's colour."""
    text, style, control = segment.text, segment.style, segment.control
    if control or not _MARKER_PATTERN.search(text):
        yield segment
        return
    for part in _MARKER_PATTERN.split(text):
        if not part:
            continue
        if part in MARKER_STYLES:
            marker_style = Style(color=MARKER_STYLES[part], bold=True)
            yield Segment(part, (style or Style()) + marker_style, control)
        else:
            yield Segment(part, style, control)


def colorize_markers(renderable: RenderableType) -> RenderableType:
    """Return a renderable that colours emoji-fallback markers (``[V]`` …).

    Args:
        renderable: Any Rich renderable that may contain ASCII markers.

    Returns:
        A wrapper renderable; marker tokens are tinted, everything else is
        passed through unchanged.

    """
    return _MarkerColorizer(renderable)
