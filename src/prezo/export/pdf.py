"""PDF export functionality with multiple backend support."""

from __future__ import annotations

import io
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from prezo.parser import parse_presentation

from .common import (
    EXIT_FAILURE,
    EXIT_SUCCESS,
    ExportError,
    check_font_availability,
    print_font_warnings,
)
from .svg import render_slide_to_svg


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
) -> Path:
    """Combine multiple SVG files into a single PDF.

    Args:
        svg_files: List of paths to SVG files
        output: Output PDF path
        backend: PDF conversion backend ("auto", "chrome", "inkscape", "cairosvg")

    Returns:
        Path to the created PDF file.

    Raises:
        ExportError: If PDF generation fails.

    """
    selected, error = _select_pdf_backend(backend)
    if error:
        raise ExportError(error)

    match selected:
        case "chrome":
            return _combine_svgs_to_pdf_chrome(svg_files, output)
        case "inkscape":
            return _combine_svgs_to_pdf_inkscape(svg_files, output)
        case _:
            return _combine_svgs_to_pdf_cairosvg(svg_files, output)


def _combine_svgs_to_pdf_chrome(svg_files: list[Path], output: Path) -> Path:
    """Combine SVGs to PDF using Chrome headless."""
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
    except ImportError as e:
        msg = "Required package not installed. Install with:\n  pip install pypdf"
        raise ExportError(msg) from e

    pdf_pages: list[Path] = []

    try:
        for svg_file in svg_files:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                pdf_path = Path(tmp.name)

            if not _convert_svg_to_pdf_chrome(svg_file, pdf_path):
                for p in pdf_pages:
                    p.unlink(missing_ok=True)
                msg = "Chrome PDF conversion failed"
                raise ExportError(msg)

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

        return output

    except ExportError:
        raise
    except Exception as e:
        for p in pdf_pages:
            p.unlink(missing_ok=True)
        msg = f"PDF generation failed: {e}"
        raise ExportError(msg) from e


def _combine_svgs_to_pdf_inkscape(svg_files: list[Path], output: Path) -> Path:
    """Combine SVGs to PDF using Inkscape."""
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
    except ImportError as e:
        msg = "Required package not installed. Install with:\n  pip install pypdf"
        raise ExportError(msg) from e

    pdf_pages: list[Path] = []

    try:
        for svg_file in svg_files:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                pdf_path = Path(tmp.name)

            if not _convert_svg_to_pdf_inkscape(svg_file, pdf_path):
                # Clean up and fail
                for p in pdf_pages:
                    p.unlink(missing_ok=True)
                msg = "Inkscape conversion failed"
                raise ExportError(msg)

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

        return output

    except ExportError:
        raise
    except Exception as e:
        for p in pdf_pages:
            p.unlink(missing_ok=True)
        msg = f"PDF generation failed: {e}"
        raise ExportError(msg) from e


def _combine_svgs_to_pdf_cairosvg(svg_files: list[Path], output: Path) -> Path:
    """Combine SVGs to PDF using CairoSVG."""
    try:
        from pypdf import PdfReader, PdfWriter  # noqa: PLC0415
    except ImportError as e:
        msg = (
            "Required packages not installed. Install with:\n"
            "  pip install cairosvg pypdf"
        )
        raise ExportError(msg) from e

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
                msg = "CairoSVG not installed. Install with:\n  pip install cairosvg"
                raise ExportError(msg)
            pdf_pages.append(io.BytesIO(pdf_bytes))

        writer = PdfWriter()
        for page_io in pdf_pages:
            reader = PdfReader(page_io)
            for page in reader.pages:
                writer.add_page(page)

        with open(output, "wb") as f:
            writer.write(f)

        return output

    except ExportError:
        raise
    except Exception as e:
        msg = f"PDF generation failed: {e}"
        raise ExportError(msg) from e


def export_to_pdf(
    source: Path,
    output: Path,
    *,
    theme: str = "dark",
    width: int = 80,
    height: int = 24,
    chrome: bool = True,
    pdf_backend: str = "auto",
) -> Path:
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
        Path to the created PDF file.

    Raises:
        ExportError: If export fails.

    """
    if not source.exists():
        msg = f"Source file not found: {source}"
        raise ExportError(msg)

    # Parse the presentation
    try:
        presentation = parse_presentation(source)
    except Exception as e:
        msg = f"Failed to parse presentation: {e}"
        raise ExportError(msg) from e

    if presentation.total_slides == 0:
        msg = "Presentation has no slides"
        raise ExportError(msg)

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

    try:
        result_path = export_to_pdf(
            source_path,
            output_path,
            theme=theme,
            width=width,
            height=height,
            chrome=chrome,
            pdf_backend=pdf_backend,
        )
        print(f"Exported to {result_path}")
        return EXIT_SUCCESS
    except ExportError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_FAILURE
