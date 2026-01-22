"""SVG rendering for slides."""

from __future__ import annotations

import io

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from prezo.layout import has_layout_blocks, parse_layout, render_layout
from prezo.themes import get_theme

# SVG template without window chrome (for printing)
# Uses Rich's template format: {var} for substitution, {{ }} for literal braces
SVG_FORMAT_NO_CHROME = """\
<svg class="rich-terminal" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
    <!-- Generated with Rich https://www.textualize.io -->
    <style>

    @font-face {{
        font-family: "Fira Code";
        src: local("FiraCode-Regular"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/FiraCode-Regular.woff2") format("woff2"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/FiraCode-Regular.woff") format("woff");
        font-style: normal;
        font-weight: 400;
    }}
    @font-face {{
        font-family: "Fira Code";
        src: local("FiraCode-Bold"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/FiraCode-Bold.woff2") format("woff2"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/FiraCode-Bold.woff") format("woff");
        font-style: bold;
        font-weight: 700;
    }}

    .{{unique_id}}-matrix {{
        font-family: Fira Code, "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", monospace;
        font-size: {{char_height}}px;
        line-height: {{line_height}}px;
        font-variant-east-asian: full-width;
        /* Disable ligatures and ensure consistent character widths */
        font-feature-settings: "liga" 0, "calt" 0, "dlig" 0;
        font-variant-ligatures: none;
        letter-spacing: 0;
        word-spacing: 0;
        white-space: pre;
    }}

    .{{unique_id}}-matrix text {{
        /* Force uniform character spacing for box-drawing chars */
        text-rendering: geometricPrecision;
    }}

    {{styles}}
    </style>

    <defs>
    <clipPath id="{{unique_id}}-clip-terminal">
      <rect x="0" y="0" width="{{width}}" height="{{height}}" />
    </clipPath>
    {{lines}}
    </defs>

    <g transform="translate(0, 0)" clip-path="url(#{{unique_id}}-clip-terminal)">
    {{backgrounds}}
    <g class="{{unique_id}}-matrix">
    {{matrix}}
    </g>
    </g>
</svg>
"""


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

    # Export to SVG
    if chrome:
        svg = console.export_svg(title=f"Slide {slide_num + 1}")
    else:
        svg = console.export_svg(code_format=SVG_FORMAT_NO_CHROME)

    # Add emoji font fallbacks to font-family declarations
    # Rich only specifies "Fira Code, monospace" which lacks emoji glyphs
    svg = svg.replace(
        "font-family: Fira Code, monospace",
        'font-family: Fira Code, "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", monospace',
    )

    # Add background color to SVG (Rich doesn't set it by default)
    # Insert a rect element right after the opening svg tag
    bg_rect = f'<rect width="100%" height="100%" fill="{theme.background}"/>'
    return svg.replace(
        'xmlns="http://www.w3.org/2000/svg">',
        f'xmlns="http://www.w3.org/2000/svg">\n    {bg_rect}',
    )
