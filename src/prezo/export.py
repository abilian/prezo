"""Export functionality for prezo presentations.

Exports presentations to PDF and HTML formats, using Rich's console
rendering for PDF and custom HTML templates for web viewing.

IMPORTANT: PDF/PNG/SVG export must be a faithful image of the TUI console.
This requires proper monospace font loading. If Fira Code is not available,
alignment may be incorrect.
"""

from __future__ import annotations

import io
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from .layout import has_layout_blocks, parse_layout, render_layout
from .parser import clean_marp_directives, extract_notes, parse_presentation
from .themes import get_theme

# Export result types
EXPORT_SUCCESS = 0
EXPORT_FAILED = 2


def check_font_availability() -> list[str]:
    """Check if required fonts are available on the system.

    Returns a list of warning messages (empty if all fonts are available).
    """
    warnings = []

    # Check for fc-list (fontconfig) to query system fonts
    fc_list_path = shutil.which("fc-list")
    if fc_list_path:
        try:
            result = subprocess.run(
                [fc_list_path, ":family"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            fonts = result.stdout.lower()

            # Check for Fira Code (primary monospace font)
            if "fira code" not in fonts and "firacode" not in fonts:
                warnings.append(
                    "Fira Code font not found. Install it for best results:\n"
                    "  macOS: brew install --cask font-fira-code\n"
                    "  Ubuntu: sudo apt install fonts-firacode\n"
                    "  Or download from: https://github.com/tonsky/FiraCode"
                )

        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            # Can't check fonts, skip warning
            pass
    else:
        # No fontconfig available (Windows or minimal system)
        # We can't easily check fonts, so just note the requirement
        warnings.append(
            "Cannot verify font availability. For correct alignment, ensure "
            "Fira Code font is installed."
        )

    return warnings


def print_font_warnings(warnings: list[str]) -> None:
    """Print font warnings to stderr."""
    if warnings:
        print("\n⚠️  Font Warning:", file=sys.stderr)
        for warning in warnings:
            for line in warning.split("\n"):
                print(f"   {line}", file=sys.stderr)
        print(
            "\n   Without proper fonts, column alignment may be incorrect in exports.",
            file=sys.stderr,
        )
        print(file=sys.stderr)


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
        font-family: Fira Code, "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", monospace;
        font-size: {char_height}px;
        line-height: {line_height}px;
        font-variant-east-asian: full-width;
        /* Disable ligatures and ensure consistent character widths */
        font-feature-settings: "liga" 0, "calt" 0, "dlig" 0;
        font-variant-ligatures: none;
        letter-spacing: 0;
        word-spacing: 0;
        white-space: pre;
    }}

    .{unique_id}-matrix text {{
        /* Force uniform character spacing for box-drawing chars */
        text-rendering: geometricPrecision;
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


def _find_chrome() -> str | None:
    """Find Chrome/Chromium executable.

    Returns:
        Path to Chrome executable, or None if not found.

    """
    # Try common Chrome executable names
    for name in ["chromium", "google-chrome", "chrome", "google-chrome-stable"]:
        path = shutil.which(name)
        if path:
            return path

    # macOS application paths
    mac_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for path in mac_paths:
        if Path(path).exists():
            return path

    return None


def _convert_svg_to_pdf_chrome(svg_file: Path, pdf_file: Path) -> bool:
    """Convert a single SVG to PDF using Chrome headless.

    Args:
        svg_file: Path to SVG file.
        pdf_file: Path for output PDF.

    Returns:
        True if successful, False otherwise.

    """
    chrome = _find_chrome()
    if not chrome:
        return False

    # Read SVG and get dimensions from viewBox
    svg_content = svg_file.read_text()
    match = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg_content)
    if match:
        width = int(float(match.group(1)))
        height = int(float(match.group(2)))
    else:
        width, height = 994, 612

    # Create HTML wrapper with proper page size
    # overflow:hidden prevents extra blank pages from slight size mismatches
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<style>
  @page {{ margin: 0; size: {width}px {height}px; }}
  html, body {{ margin: 0; padding: 0; overflow: hidden; height: {height}px; width: {width}px; }}
  svg {{ display: block; }}
</style>
</head>
<body>
{svg_content}
</body>
</html>"""

    # Write HTML to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False
    ) as html_file:
        html_file.write(html_content)
        html_path = Path(html_file.name)

    try:
        result = subprocess.run(
            [
                chrome,
                "--headless",
                "--disable-gpu",
                "--password-store=basic",
                "--use-mock-keychain",
                f"--print-to-pdf={pdf_file}",
                "--no-pdf-header-footer",
                str(html_path),
            ],
            capture_output=True,
            timeout=60,
            check=False,
        )
        return result.returncode == 0 and pdf_file.exists()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False
    finally:
        html_path.unlink(missing_ok=True)


def _convert_svg_to_pdf_inkscape(svg_file: Path, pdf_file: Path) -> bool:
    """Convert a single SVG to PDF using Inkscape.

    Args:
        svg_file: Path to SVG file.
        pdf_file: Path for output PDF.

    Returns:
        True if successful, False otherwise.

    """
    inkscape = shutil.which("inkscape")
    if not inkscape:
        return False

    try:
        result = subprocess.run(
            [
                inkscape,
                str(svg_file),
                f"--export-filename={pdf_file}",
                "--export-type=pdf",
            ],
            capture_output=True,
            timeout=60,
            check=False,
        )
        return result.returncode == 0 and pdf_file.exists()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def _convert_svg_to_pdf_cairosvg(svg_file: Path) -> bytes | None:
    """Convert a single SVG to PDF using CairoSVG.

    Args:
        svg_file: Path to SVG file.

    Returns:
        PDF bytes if successful, None otherwise.

    """
    try:
        import cairosvg  # noqa: PLC0415
    except ImportError:
        return None

    # CairoSVG doesn't properly support textLength, so we strip it
    svg_content = svg_file.read_text()
    svg_content = re.sub(r'\s*textLength="[^"]*"', "", svg_content)
    svg_content = re.sub(r'\s*lengthAdjust="[^"]*"', "", svg_content)

    return cairosvg.svg2pdf(bytestring=svg_content.encode("utf-8"))


def _select_pdf_backend(backend: str) -> tuple[str, str | None]:
    """Select the PDF backend to use.

    Args:
        backend: Requested backend ("auto", "chrome", "inkscape", "cairosvg")

    Returns:
        Tuple of (selected_backend, error_message). Error is None if OK.

    """
    checks = {
        "chrome": (
            _find_chrome,
            "Chrome/Chromium not found. Install it or use a different backend.",
        ),
        "inkscape": (
            lambda: shutil.which("inkscape"),
            "Inkscape not found. Install it or use --pdf-backend=cairosvg",
        ),
    }

    if backend in checks:
        check_fn, error_msg = checks[backend]
        return (backend, None) if check_fn() else ("", error_msg)

    if backend == "cairosvg":
        return "cairosvg", None

    # auto: prefer Chrome > Inkscape > CairoSVG
    for name, (check_fn, _) in checks.items():
        if check_fn():
            return name, None
    return "cairosvg", None


def combine_svgs_to_pdf(
    svg_files: list[Path], output: Path, *, backend: str = "auto"
) -> tuple[int, str]:
    """Combine multiple SVG files into a single PDF.

    Args:
        svg_files: List of paths to SVG files
        output: Output PDF path
        backend: PDF conversion backend ("auto", "chrome", "inkscape", "cairosvg")

    Returns:
        Tuple of (exit_code, message)

    """
    selected, error = _select_pdf_backend(backend)
    if error:
        return EXPORT_FAILED, error

    if selected == "chrome":
        return _combine_svgs_to_pdf_chrome(svg_files, output)
    if selected == "inkscape":
        return _combine_svgs_to_pdf_inkscape(svg_files, output)
    return _combine_svgs_to_pdf_cairosvg(svg_files, output)


def _combine_svgs_to_pdf_chrome(svg_files: list[Path], output: Path) -> tuple[int, str]:
    """Combine SVGs to PDF using Chrome headless."""
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
    except ImportError:
        return EXPORT_FAILED, (
            "Required package not installed. Install with:\n  pip install pypdf"
        )

    pdf_pages: list[Path] = []

    try:
        for svg_file in svg_files:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                pdf_path = Path(tmp.name)

            if not _convert_svg_to_pdf_chrome(svg_file, pdf_path):
                for p in pdf_pages:
                    p.unlink(missing_ok=True)
                return EXPORT_FAILED, "Chrome PDF conversion failed"

            pdf_pages.append(pdf_path)

        # Combine all pages
        writer = PdfWriter()
        for pdf_path in pdf_pages:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                writer.add_page(page)

        with open(output, "wb") as f:
            writer.write(f)

        # Clean up temp files
        for p in pdf_pages:
            p.unlink(missing_ok=True)

        return EXPORT_SUCCESS, f"Exported {len(svg_files)} slides to {output}"

    except Exception as e:
        for p in pdf_pages:
            p.unlink(missing_ok=True)
        return EXPORT_FAILED, f"PDF generation failed: {e}"


def _combine_svgs_to_pdf_inkscape(
    svg_files: list[Path], output: Path
) -> tuple[int, str]:
    """Combine SVGs to PDF using Inkscape."""
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
    except ImportError:
        return EXPORT_FAILED, (
            "Required package not installed. Install with:\n  pip install pypdf"
        )

    pdf_pages: list[Path] = []

    try:
        for svg_file in svg_files:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                pdf_path = Path(tmp.name)

            if not _convert_svg_to_pdf_inkscape(svg_file, pdf_path):
                # Clean up and fail
                for p in pdf_pages:
                    p.unlink(missing_ok=True)
                return EXPORT_FAILED, "Inkscape conversion failed"

            pdf_pages.append(pdf_path)

        # Combine all pages
        writer = PdfWriter()
        for pdf_path in pdf_pages:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                writer.add_page(page)

        with open(output, "wb") as f:
            writer.write(f)

        # Clean up temp files
        for p in pdf_pages:
            p.unlink(missing_ok=True)

        return EXPORT_SUCCESS, f"Exported {len(svg_files)} slides to {output}"

    except Exception as e:
        for p in pdf_pages:
            p.unlink(missing_ok=True)
        return EXPORT_FAILED, f"PDF generation failed: {e}"


def _combine_svgs_to_pdf_cairosvg(
    svg_files: list[Path], output: Path
) -> tuple[int, str]:
    """Combine SVGs to PDF using CairoSVG."""
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
    except ImportError:
        return EXPORT_FAILED, (
            "Required packages not installed. Install with:\n"
            "  pip install cairosvg pypdf"
        )

    # Warn about CairoSVG limitations
    print(
        "⚠️  Using CairoSVG backend. For better alignment, install Inkscape "
        "or use --pdf-backend=inkscape",
        file=sys.stderr,
    )

    pdf_pages = []

    try:
        for svg_file in svg_files:
            pdf_bytes = _convert_svg_to_pdf_cairosvg(svg_file)
            if pdf_bytes is None:
                return EXPORT_FAILED, (
                    "CairoSVG not installed. Install with:\n  pip install cairosvg"
                )
            pdf_pages.append(io.BytesIO(pdf_bytes))

        writer = PdfWriter()
        for page_io in pdf_pages:
            reader = PdfReader(page_io)
            for page in reader.pages:
                writer.add_page(page)

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
    pdf_backend: str = "auto",
) -> tuple[int, str]:
    """Export presentation to PDF matching TUI appearance.

    Args:
        source: Path to the markdown presentation
        output: Path for the output PDF
        theme: Theme to use for rendering
        width: Console width in characters
        height: Console height in lines
        chrome: If True, include window decorations; if False, plain output for printing
        pdf_backend: Backend for PDF conversion ("auto", "inkscape", "cairosvg")

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

    # Check font availability and warn if needed
    font_warnings = check_font_availability()
    print_font_warnings(font_warnings)

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
        return combine_svgs_to_pdf(svg_files, output, backend=pdf_backend)


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
        /* Multi-column layouts */
        .columns {{
            display: flex;
            gap: 2rem;
            align-items: flex-start;
        }}
        .columns > div {{
            flex: 1;
            min-width: 0;
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
        # Use raw_content and clean with keep_divs=True to preserve column layouts
        slide_content, _ = extract_notes(slide.raw_content)
        cleaned_content = clean_marp_directives(slide_content, keep_divs=True)
        content_html = render_slide_to_html(cleaned_content)

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
    pdf_backend: str = "auto",
) -> int:
    """Run PDF export from command line.

    Args:
        source: Path to the markdown presentation (string)
        output: Optional path for the output PDF (string)
        theme: Theme to use for rendering
        width: Console width in characters
        height: Console height in lines
        chrome: If True, include window decorations; if False, plain output for printing
        pdf_backend: Backend for PDF conversion ("auto", "inkscape", "cairosvg")

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
        pdf_backend=pdf_backend,
    )
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

    # Check font availability and warn if needed (for PNG export)
    if output_format == "png":
        font_warnings = check_font_availability()
        print_font_warnings(font_warnings)

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
