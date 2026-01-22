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

"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import StringIO
from typing import TYPE_CHECKING, Literal

from rich.console import Console, ConsoleOptions, Group, RenderResult
from rich.markdown import Markdown
from rich.measure import Measurement
from rich.text import Text

if TYPE_CHECKING:
    from rich.console import RenderableType

# -----------------------------------------------------------------------------
# Data Types
# -----------------------------------------------------------------------------


@dataclass
class LayoutBlock:
    """A block of content with layout information."""

    type: Literal["plain", "columns", "column", "center"]
    content: str = ""  # Raw markdown content (for leaf blocks)
    children: list[LayoutBlock] = field(default_factory=list)
    width_percent: int = 0  # For column blocks (0 = auto/equal)


# -----------------------------------------------------------------------------
# Parser
# -----------------------------------------------------------------------------

# Pattern for opening fenced div: ::: type [width]
OPEN_PATTERN = re.compile(r"^:::\s*(\w+)(?:\s+(\d+))?\s*$")
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
            width = int(match.group(2)) if match.group(2) else 0

            # Find matching close and nested content
            block, end_idx = _parse_fenced_block(lines, i, block_type, width)
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


def _parse_fenced_block(
    lines: list[str], start: int, block_type: str, width: int
) -> tuple[LayoutBlock | None, int]:
    """Parse a fenced div block starting at the given line.

    Args:
        lines: All lines of content.
        start: Starting line index (the opening :::).
        block_type: The type from ::: type.
        width: Width percentage if specified.

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

    # For columns/column types, parse children
    if block_type in ("columns", "column", "center"):
        block = LayoutBlock(
            type=block_type,  # type: ignore[arg-type]
            width_percent=width,
        )

        if block_type == "columns":
            # Parse children (should be column blocks)
            block.children = parse_layout(inner_content)
        elif block_type == "column":
            # Column contains markdown content, but might have nested structure
            # For now, treat as plain content
            block.content = inner_content.strip()
        elif block_type == "center":
            block.content = inner_content.strip()

        return block, i

    # Unknown block type - treat content as plain
    return LayoutBlock(type="plain", content=inner_content.strip()), i


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

        # Render markdown content
        if column.content:
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
        match block.type:
            case "plain":
                renderables.append(Markdown(block.content))
            case "columns":
                # Filter to only column children
                columns = [c for c in block.children if c.type == "column"]
                if columns:
                    renderables.append(ColumnsRenderable(columns))
                # Also render any non-column children (plain text between columns)
                for child in block.children:
                    if child.type == "plain":
                        renderables.append(Markdown(child.content))
            case "center":
                renderables.append(CenterRenderable(block.content))
            case "column":
                # Standalone column (shouldn't happen normally)
                renderables.append(Markdown(block.content))

    if len(renderables) == 1:
        return renderables[0]
    return Group(*renderables)


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

# ANSI escape sequence pattern
_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def _visible_length(text: str) -> int:
    """Calculate visible length of text, excluding ANSI codes.

    Args:
        text: Text possibly containing ANSI escape codes.

    Returns:
        Visible character count.

    """
    return len(_ANSI_PATTERN.sub("", text))
