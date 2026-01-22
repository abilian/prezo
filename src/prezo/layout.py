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

from rich.cells import cell_len
from rich.console import Console, ConsoleOptions, Group, RenderResult
from rich.markdown import Markdown
from rich.measure import Measurement
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

if TYPE_CHECKING:
    from rich.console import RenderableType

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
        style = unquoted_arg if unquoted_arg else "single"
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
        yield Text("")
        md = Markdown(self.content)
        panel = Panel(md, title=self.title if self.title else None)
        yield panel
        yield Text("")

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


def _render_block(block: LayoutBlock) -> list[RenderableType]:
    """Render a single block to Rich renderables.

    Args:
        block: A LayoutBlock to render.

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
                result.append(Markdown(child.content))
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

    # Default: plain markdown (for "plain" and standalone "column")
    return [Markdown(block.content)]


def render_layout(
    blocks: list[LayoutBlock],
) -> RenderableType:
    """Render layout blocks to a Rich renderable.

    Args:
        blocks: List of LayoutBlocks from parse_layout().

    Returns:
        Rich renderable representing the layout.

    """
    renderables: list[RenderableType] = []

    for block in blocks:
        renderables.extend(_render_block(block))

    if len(renderables) == 1:
        return renderables[0]
    return Group(*renderables)


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

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
    return cell_len(clean_text)
