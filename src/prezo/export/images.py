"""Image (PNG/SVG) export functionality."""

from __future__ import annotations

import sys
from pathlib import Path

from prezo.parser import parse_presentation

from .common import (
    EXPORT_FAILED,
    EXPORT_SUCCESS,
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
        print(f"error: {message}", file=sys.stderr)

    return code
