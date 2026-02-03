"""SVG rendering for slides."""

from __future__ import annotations

import io
import re

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from prezo.layout import has_layout_blocks, parse_layout, render_layout
from prezo.themes import get_theme

# Patterns for stripping window chrome from SVG
# Window border rect with rounded corners
_WINDOW_BORDER_PATTERN = re.compile(
    r'<rect fill="[^"]*" stroke="rgba\(255,255,255,[^"]*\)" '
    r'stroke-width="1" x="1" y="1" [^/]*/>'
)
# Title text element
_TITLE_TEXT_PATTERN = re.compile(r'<text class="[^"]*-title"[^>]*>[^<]*</text>')
# Traffic light buttons group
_TRAFFIC_LIGHTS_PATTERN = re.compile(
    r'<g transform="translate\(26,22\)">\s*'
    r'<circle[^/]*/>\s*<circle[^/]*/>\s*<circle[^/]*/>\s*</g>'
)
# Content group transform (to adjust offset)
_CONTENT_TRANSFORM_PATTERN = re.compile(
    r'<g transform="translate\((\d+(?:\.\d+)?), (\d+(?:\.\d+)?)\)" '
    r'clip-path="url\(#([^"]+)\)">'
)


def _strip_window_chrome(svg: str) -> str:
    """Remove window decorations from SVG for printing.

    Removes:
    - Window border (rounded rect with stroke)
    - Title text
    - Traffic light buttons (red/yellow/green circles)

    Also adjusts the content position to start at origin.

    Args:
        svg: SVG string with window chrome.

    Returns:
        SVG string without window chrome.

    """
    # Remove window border
    svg = _WINDOW_BORDER_PATTERN.sub("", svg)

    # Remove title text
    svg = _TITLE_TEXT_PATTERN.sub("", svg)

    # Remove traffic lights
    svg = _TRAFFIC_LIGHTS_PATTERN.sub("", svg)

    # Adjust content transform to remove offset
    # The content is typically at translate(9, 41) with chrome
    # Move it to translate(0, 0) for clean output
    def adjust_transform(match: re.Match) -> str:
        clip_id = match.group(3)
        return f'<g transform="translate(0, 0)" clip-path="url(#{clip_id})">'

    svg = _CONTENT_TRANSFORM_PATTERN.sub(adjust_transform, svg)

    return svg


def render_slide_to_svg(
    content: str,
    slide_num: int,
    total_slides: int,
    *,
    theme_name: str = "dark",
    width: int = 80,
    height: int = 24,
    chrome: bool = True,
) -> str:
    """Render a single slide to SVG using Rich console.

    Args:
        content: The markdown content of the slide
        slide_num: Current slide number (0-indexed)
        total_slides: Total number of slides
        theme_name: Theme to use for rendering
        width: Console width in characters
        height: Console height in lines
        chrome: If True, include window decorations; if False, plain SVG for printing

    Returns:
        SVG string of the rendered slide

    """
    theme = get_theme(theme_name)

    # Create a console that records output (file=StringIO suppresses terminal output)
    console = Console(
        width=width,
        record=True,
        force_terminal=True,
        color_system="truecolor",
        file=io.StringIO(),  # Suppress terminal output
    )

    # Base style for the entire slide (background color)
    base_style = Style(color=theme.text, bgcolor=theme.background)

    # Render the content (with layout support)
    if has_layout_blocks(content):
        blocks = parse_layout(content)
        slide_content = render_layout(blocks)
    else:
        slide_content = Markdown(content)

    # Create a panel with the slide content (height - 2 for status bar and padding)
    panel_height = height - 2
    panel = Panel(
        slide_content,
        title=f"[{theme.text_muted}]Slide {slide_num + 1}/{total_slides}[/]",
        title_align="right",
        border_style=Style(color=theme.primary),
        style=Style(color=theme.text, bgcolor=theme.surface),
        padding=(1, 2),
        expand=True,
        height=panel_height,
    )

    # Print to the recording console with background
    console.print(panel, style=base_style)

    # Add status bar at the bottom
    progress = (slide_num + 1) / total_slides
    bar_width = 20
    filled = int(progress * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    status_text = f" {bar} {slide_num + 1}/{total_slides} "
    # Pad status bar to full width
    status_text = status_text.ljust(width)
    status = Text(status_text, style=Style(bgcolor=theme.primary, color=theme.text))
    console.print(status, style=base_style)

    # Export to SVG (always with Rich's default chrome first)
    svg = console.export_svg(title=f"Slide {slide_num + 1}")

    # Add emoji font fallbacks to font-family declarations
    # Rich only specifies "Fira Code, monospace" which lacks emoji glyphs
    svg = svg.replace(
        "font-family: Fira Code, monospace",
        'font-family: Fira Code, "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", monospace',
    )

    # Add background color to SVG (Rich doesn't set it by default)
    # Insert a rect element right after the opening svg tag
    bg_rect = f'<rect width="100%" height="100%" fill="{theme.background}"/>'
    svg = svg.replace(
        'xmlns="http://www.w3.org/2000/svg">',
        f'xmlns="http://www.w3.org/2000/svg">\n    {bg_rect}',
    )

    # Remove window chrome if requested (for printing)
    if not chrome:
        svg = _strip_window_chrome(svg)

    return svg
