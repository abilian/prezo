"""Export functionality for prezo presentations.

Exports presentations to PDF and HTML formats, using Rich's console
rendering for PDF and custom HTML templates for web viewing.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from .parser import parse_presentation
from .themes import get_theme

# Export result types
EXPORT_SUCCESS = 0
EXPORT_FAILED = 2

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

    .{unique_id}-matrix {{
        font-family: Fira Code, monospace;
        font-size: {char_height}px;
        line-height: {line_height}px;
        font-variant-east-asian: full-width;
    }}

    {styles}
    </style>

    <defs>
    <clipPath id="{unique_id}-clip-terminal">
      <rect x="0" y="0" width="{width}" height="{height}" />
    </clipPath>
    {lines}
    </defs>

    <g transform="translate(0, 0)" clip-path="url(#{unique_id}-clip-terminal)">
    {backgrounds}
    <g class="{unique_id}-matrix">
    {matrix}
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

    # Render the markdown content
    md = Markdown(content)

    # Create a panel with the slide content (height - 2 for status bar and padding)
    panel_height = height - 2
    panel = Panel(
        md,
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

    # Add background color to SVG (Rich doesn't set it by default)
    # Insert a rect element right after the opening svg tag
    bg_rect = f'<rect width="100%" height="100%" fill="{theme.background}"/>'
    return svg.replace(
        'xmlns="http://www.w3.org/2000/svg">',
        f'xmlns="http://www.w3.org/2000/svg">\n    {bg_rect}',
    )


def combine_svgs_to_pdf(svg_files: list[Path], output: Path) -> tuple[int, str]:
    """Combine multiple SVG files into a single PDF.

    Args:
        svg_files: List of paths to SVG files
        output: Output PDF path

    Returns:
        Tuple of (exit_code, message)

    """
    try:
        import cairosvg  # noqa: PLC0415
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
    except ImportError:
        return EXPORT_FAILED, (
            "Required packages not installed. Install with:\n"
            "  pip install cairosvg pypdf"
        )

    pdf_pages = []

    try:
        # Convert each SVG to a PDF page
        for svg_file in svg_files:
            pdf_bytes = cairosvg.svg2pdf(url=str(svg_file))
            assert pdf_bytes is not None
            pdf_pages.append(io.BytesIO(pdf_bytes))

        # Combine all pages into one PDF
        writer = PdfWriter()
        for page_io in pdf_pages:
            reader = PdfReader(page_io)
            for page in reader.pages:
                writer.add_page(page)

        # Write the combined PDF
        with open(output, "wb") as f:
            writer.write(f)

        return EXPORT_SUCCESS, f"Exported {len(svg_files)} slides to {output}"

    except Exception as e:
        return EXPORT_FAILED, f"PDF generation failed: {e}"


def export_to_pdf(
    source: Path,
    output: Path,
    *,
    theme: str = "dark",
    width: int = 80,
    height: int = 24,
    chrome: bool = True,
) -> tuple[int, str]:
    """Export presentation to PDF matching TUI appearance.

    Args:
        source: Path to the markdown presentation
        output: Path for the output PDF
        theme: Theme to use for rendering
        width: Console width in characters
        height: Console height in lines
        chrome: If True, include window decorations; if False, plain output for printing

    Returns:
        Tuple of (exit_code, message)

    """
    if not source.exists():
        return EXPORT_FAILED, f"Source file not found: {source}"

    # Parse the presentation
    try:
        presentation = parse_presentation(source)
    except Exception as e:
        return EXPORT_FAILED, f"Failed to parse presentation: {e}"

    if presentation.total_slides == 0:
        return EXPORT_FAILED, "Presentation has no slides"

    # Create temporary directory for SVG files
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        svg_files = []

        # Render each slide to SVG
        for i, slide in enumerate(presentation.slides):
            svg_content = render_slide_to_svg(
                slide.content,
                i,
                presentation.total_slides,
                theme_name=theme,
                width=width,
                height=height,
                chrome=chrome,
            )

            svg_file = tmpdir / f"slide_{i:04d}.svg"
            svg_file.write_text(svg_content)
            svg_files.append(svg_file)

        # Combine into PDF
        return combine_svgs_to_pdf(svg_files, output)


# HTML export templates
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: {background};
            color: {text};
            min-height: 100vh;
        }}
        .slides {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        .slide {{
            background: {surface};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 3rem 4rem;
            margin-bottom: 3rem;
            min-height: 70vh;
            display: flex;
            flex-direction: column;
            page-break-after: always;
        }}
        .slide-number {{
            color: {text_muted};
            font-size: 0.9rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid {border};
        }}
        .slide-content {{
            flex: 1;
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 1.5rem;
            color: {primary};
        }}
        h2 {{
            font-size: 2rem;
            margin-bottom: 1.2rem;
            color: {primary};
        }}
        h3 {{
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: {text};
        }}
        p {{
            font-size: 1.2rem;
            line-height: 1.6;
            margin-bottom: 1rem;
        }}
        ul, ol {{
            margin: 1rem 0;
            padding-left: 2rem;
        }}
        li {{
            font-size: 1.2rem;
            line-height: 1.6;
            margin-bottom: 0.5rem;
        }}
        pre {{
            background: {background};
            border-radius: 4px;
            padding: 1rem;
            overflow-x: auto;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 1rem;
            margin: 1rem 0;
        }}
        code {{
            font-family: 'Fira Code', 'Consolas', monospace;
            background: {background};
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-size: 0.95em;
        }}
        pre code {{
            padding: 0;
            background: none;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }}
        th, td {{
            border: 1px solid {border};
            padding: 0.75rem;
            text-align: left;
        }}
        th {{
            background: {background};
        }}
        blockquote {{
            border-left: 4px solid {primary};
            padding-left: 1rem;
            margin: 1rem 0;
            font-style: italic;
            color: {text_muted};
        }}
        a {{
            color: {primary};
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        .notes {{
            margin-top: 2rem;
            padding: 1rem;
            background: {background};
            border-radius: 4px;
            font-size: 0.9rem;
            color: {text_muted};
        }}
        .notes-title {{
            font-weight: bold;
            margin-bottom: 0.5rem;
        }}
        @media print {{
            .slide {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}
            body {{
                background: white;
                color: black;
            }}
        }}
    </style>
</head>
<body>
    <div class="slides">
{slides}
    </div>
</body>
</html>
"""

SLIDE_TEMPLATE = """\
        <div class="slide" id="slide-{num}">
            <div class="slide-number">Slide {display_num} of {total}</div>
            <div class="slide-content">
{content}
            </div>
{notes}
        </div>
"""

NOTES_TEMPLATE = """\
            <div class="notes">
                <div class="notes-title">Presenter Notes</div>
{notes_content}
            </div>
"""


def render_slide_to_html(content: str) -> str:
    """Convert markdown content to basic HTML.

    Args:
        content: Markdown content of the slide.

    Returns:
        HTML string for the slide content.

    """
    try:
        import markdown  # noqa: PLC0415

        html = markdown.markdown(
            content,
            extensions=["tables", "fenced_code", "codehilite"],
        )
    except ImportError:
        # Fallback: basic markdown-to-html conversion
        import html as html_mod  # noqa: PLC0415

        html = html_mod.escape(content)
        # Basic transformations
        html = html.replace("\n\n", "</p><p>")
        html = f"<p>{html}</p>"

    return html


def export_to_html(
    source: Path,
    output: Path,
    *,
    theme: str = "dark",
    include_notes: bool = False,
) -> tuple[int, str]:
    """Export presentation to HTML.

    Args:
        source: Path to the markdown presentation.
        output: Path for the output HTML file.
        theme: Theme to use for styling.
        include_notes: Whether to include presenter notes.

    Returns:
        Tuple of (exit_code, message).

    """
    if not source.exists():
        return EXPORT_FAILED, f"Source file not found: {source}"

    try:
        presentation = parse_presentation(source)
    except Exception as e:
        return EXPORT_FAILED, f"Failed to parse presentation: {e}"

    if presentation.total_slides == 0:
        return EXPORT_FAILED, "Presentation has no slides"

    theme_obj = get_theme(theme)

    # Render each slide
    slides_html = []
    for i, slide in enumerate(presentation.slides):
        content_html = render_slide_to_html(slide.content)

        # Handle notes
        notes_html = ""
        if include_notes and slide.notes:
            notes_content = render_slide_to_html(slide.notes)
            notes_html = NOTES_TEMPLATE.format(notes_content=notes_content)

        slide_html = SLIDE_TEMPLATE.format(
            num=i,
            display_num=i + 1,
            total=presentation.total_slides,
            content=content_html,
            notes=notes_html,
        )
        slides_html.append(slide_html)

    # Build final HTML
    title = presentation.title or source.stem
    html = HTML_TEMPLATE.format(
        title=title,
        background=theme_obj.background,
        surface=theme_obj.surface,
        text=theme_obj.text,
        text_muted=theme_obj.text_muted,
        primary=theme_obj.primary,
        border=theme_obj.text_muted,
        slides="\n".join(slides_html),
    )

    try:
        output.write_text(html)
        return (
            EXPORT_SUCCESS,
            f"Exported {presentation.total_slides} slides to {output}",
        )
    except Exception as e:
        return EXPORT_FAILED, f"Failed to write HTML: {e}"


def run_export(
    source: str,
    output: str | None = None,
    *,
    theme: str = "dark",
    width: int = 80,
    height: int = 24,
    chrome: bool = True,
) -> int:
    """Run PDF export from command line.

    Args:
        source: Path to the markdown presentation (string)
        output: Optional path for the output PDF (string)
        theme: Theme to use for rendering
        width: Console width in characters
        height: Console height in lines
        chrome: If True, include window decorations; if False, plain output for printing

    Returns:
        Exit code (0 for success)

    """
    source_path = Path(source)
    output_path = Path(output) if output else source_path.with_suffix(".pdf")

    code, _message = export_to_pdf(
        source_path,
        output_path,
        theme=theme,
        width=width,
        height=height,
        chrome=chrome,
    )
    if code == EXPORT_SUCCESS:
        pass
    else:
        pass
    return code


def run_html_export(
    source: str,
    output: str | None = None,
    *,
    theme: str = "light",
    include_notes: bool = False,
) -> int:
    """Run HTML export from command line.

    Args:
        source: Path to the markdown presentation (string).
        output: Optional path for the output HTML (string).
        theme: Theme to use for styling.
        include_notes: Whether to include presenter notes.

    Returns:
        Exit code (0 for success).

    """
    source_path = Path(source)
    output_path = Path(output) if output else source_path.with_suffix(".html")

    code, _message = export_to_html(
        source_path,
        output_path,
        theme=theme,
        include_notes=include_notes,
    )
    return code


def export_slide_to_image(
    content: str,
    slide_num: int,
    total_slides: int,
    output_path: Path,
    *,
    output_format: str = "png",
    theme_name: str = "dark",
    width: int = 80,
    height: int = 24,
    chrome: bool = True,
    scale: float = 1.0,
) -> tuple[int, str]:
    """Export a single slide to PNG or SVG.

    Args:
        content: The markdown content of the slide.
        slide_num: Current slide number (0-indexed).
        total_slides: Total number of slides.
        output_path: Path to save the image.
        output_format: Output format ('png' or 'svg').
        theme_name: Theme to use for rendering.
        width: Console width in characters.
        height: Console height in lines.
        chrome: If True, include window decorations.
        scale: Scale factor for PNG output (e.g., 2.0 for 2x resolution).

    Returns:
        Tuple of (exit_code, message).

    """
    # Generate SVG
    svg_content = render_slide_to_svg(
        content,
        slide_num,
        total_slides,
        theme_name=theme_name,
        width=width,
        height=height,
        chrome=chrome,
    )

    if output_format == "svg":
        try:
            output_path.write_text(svg_content)
            return EXPORT_SUCCESS, f"Exported slide {slide_num + 1} to {output_path}"
        except Exception as e:
            return EXPORT_FAILED, f"Failed to write SVG: {e}"

    # Convert SVG to PNG
    try:
        import cairosvg  # noqa: PLC0415
    except ImportError:
        return EXPORT_FAILED, (
            "PNG export requires cairosvg.\nInstall with: pip install prezo[export]"
        )

    try:
        png_data = cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"),
            scale=scale,
        )
        if png_data is None:
            return EXPORT_FAILED, "PNG conversion returned no data"
        output_path.write_bytes(png_data)
        return EXPORT_SUCCESS, f"Exported slide {slide_num + 1} to {output_path}"
    except Exception as e:
        return EXPORT_FAILED, f"Failed to convert to PNG: {e}"


def export_to_images(
    source: Path,
    output: Path | None = None,
    *,
    output_format: str = "png",
    theme: str = "dark",
    width: int = 80,
    height: int = 24,
    chrome: bool = True,
    slide_num: int | None = None,
    scale: float = 2.0,
) -> tuple[int, str]:
    """Export presentation slides to images.

    Args:
        source: Path to the markdown presentation.
        output: Output path (file for single slide, directory for all).
        output_format: Output format ('png' or 'svg').
        theme: Theme to use for rendering.
        width: Console width in characters.
        height: Console height in lines.
        chrome: If True, include window decorations.
        slide_num: If set, export only this slide (1-indexed).
        scale: Scale factor for PNG output (default 2.0 for higher resolution).

    Returns:
        Tuple of (exit_code, message).

    """
    # Parse presentation
    try:
        presentation = parse_presentation(source)
    except Exception as e:
        return EXPORT_FAILED, f"Failed to read {source}: {e}"

    if presentation.total_slides == 0:
        return EXPORT_FAILED, "No slides found in presentation"

    # Single slide export
    if slide_num is not None:
        if slide_num < 1 or slide_num > presentation.total_slides:
            return EXPORT_FAILED, (
                f"Invalid slide number: {slide_num}. "
                f"Presentation has {presentation.total_slides} slides."
            )

        slide_idx = slide_num - 1
        slide = presentation.slides[slide_idx]

        out_path = Path(output) if output else source.with_suffix(f".{output_format}")

        return export_slide_to_image(
            slide.content,
            slide_idx,
            presentation.total_slides,
            out_path,
            output_format=output_format,
            theme_name=theme,
            width=width,
            height=height,
            chrome=chrome,
            scale=scale,
        )

    # Export all slides
    if output:
        out_dir = Path(output)
        if out_dir.suffix:  # Has extension, treat as file prefix
            prefix = out_dir.stem  # Get stem before reassigning
            out_dir = out_dir.parent
        else:
            prefix = source.stem
    else:
        out_dir = source.parent
        prefix = source.stem

    # Create output directory if needed
    out_dir.mkdir(parents=True, exist_ok=True)

    exported = 0
    for i, slide in enumerate(presentation.slides):
        out_path = out_dir / f"{prefix}_{i + 1:03d}.{output_format}"
        code, msg = export_slide_to_image(
            slide.content,
            i,
            presentation.total_slides,
            out_path,
            output_format=output_format,
            theme_name=theme,
            width=width,
            height=height,
            chrome=chrome,
            scale=scale,
        )
        if code != EXPORT_SUCCESS:
            return code, msg
        exported += 1

    return EXPORT_SUCCESS, f"Exported {exported} slides to {out_dir}/"


def run_image_export(
    source: str,
    output: str | None = None,
    *,
    output_format: str = "png",
    theme: str = "dark",
    width: int = 80,
    height: int = 24,
    chrome: bool = True,
    slide_num: int | None = None,
    scale: float = 2.0,
) -> int:
    """Run PNG/SVG export from command line.

    Args:
        source: Path to the markdown presentation.
        output: Optional output path (file or directory).
        output_format: Output format ('png' or 'svg').
        theme: Theme to use for rendering.
        width: Console width in characters.
        height: Console height in lines.
        chrome: If True, include window decorations.
        slide_num: If set, export only this slide (1-indexed).
        scale: Scale factor for PNG output (default 2.0 for higher resolution).

    Returns:
        Exit code (0 for success).

    """
    source_path = Path(source)
    output_path = Path(output) if output else None

    code, message = export_to_images(
        source_path,
        output_path,
        output_format=output_format,
        theme=theme,
        width=width,
        height=height,
        chrome=chrome,
        slide_num=slide_num,
        scale=scale,
    )

    if code == EXPORT_SUCCESS:
        print(message)
    else:
        print(f"error: {message}", file=__import__("sys").stderr)

    return code
