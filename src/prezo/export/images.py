"""Image (PNG/SVG) export functionality."""

from __future__ import annotations

import sys
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
) -> Path:
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
        Path to the created image file.

    Raises:
        ExportError: If export fails.

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
            return output_path
        except Exception as e:
            msg = f"Failed to write SVG: {e}"
            raise ExportError(msg) from e

    # Convert SVG to PNG
    try:
        import cairosvg  # noqa: PLC0415
    except ImportError as e:
        msg = "PNG export requires cairosvg.\nInstall with: pip install prezo[export]"
        raise ExportError(msg) from e

    try:
        png_data = cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"),
            scale=scale,
        )
        if png_data is None:
            msg = "PNG conversion returned no data"
            raise ExportError(msg)
        output_path.write_bytes(png_data)
        return output_path
    except ExportError:
        raise
    except Exception as e:
        msg = f"Failed to convert to PNG: {e}"
        raise ExportError(msg) from e


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
) -> list[Path]:
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
        List of paths to the created image files.

    Raises:
        ExportError: If export fails.

    """
    # Parse presentation
    try:
        presentation = parse_presentation(source)
    except Exception as e:
        msg = f"Failed to read {source}: {e}"
        raise ExportError(msg) from e

    if presentation.total_slides == 0:
        msg = "No slides found in presentation"
        raise ExportError(msg)

    # Check font availability and warn if needed (for PNG export)
    if output_format == "png":
        font_warnings = check_font_availability()
        print_font_warnings(font_warnings)

    # Single slide export
    if slide_num is not None:
        if slide_num < 1 or slide_num > presentation.total_slides:
            msg = (
                f"Invalid slide number: {slide_num}. "
                f"Presentation has {presentation.total_slides} slides."
            )
            raise ExportError(msg)

        slide_idx = slide_num - 1
        slide = presentation.slides[slide_idx]

        out_path = Path(output) if output else source.with_suffix(f".{output_format}")

        result_path = export_slide_to_image(
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
        return [result_path]

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

    exported_paths = []
    for i, slide in enumerate(presentation.slides):
        out_path = out_dir / f"{prefix}_{i + 1:03d}.{output_format}"
        result_path = export_slide_to_image(
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
        exported_paths.append(result_path)

    return exported_paths


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

    try:
        exported_paths = export_to_images(
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
        if len(exported_paths) == 1:
            print(f"Exported to {exported_paths[0]}")
        else:
            print(
                f"Exported {len(exported_paths)} slides to {exported_paths[0].parent}/"
            )
        return EXIT_SUCCESS
    except ExportError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_FAILURE
