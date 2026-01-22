"""Export functionality for prezo presentations.

Exports presentations to PDF, HTML, PNG, and SVG formats.

IMPORTANT: PDF/PNG/SVG export must be a faithful image of the TUI console.
This requires proper monospace font loading. If Fira Code is not available,
alignment may be incorrect.
"""

from __future__ import annotations

from .common import (
    EXPORT_FAILED,
    EXPORT_SUCCESS,
    check_font_availability,
    print_font_warnings,
)
from .html import export_to_html, render_slide_to_html, run_html_export
from .images import export_slide_to_image, export_to_images, run_image_export
from .pdf import combine_svgs_to_pdf, export_to_pdf, run_export
from .svg import render_slide_to_svg

__all__ = [
    "EXPORT_FAILED",
    "EXPORT_SUCCESS",
    "check_font_availability",
    "combine_svgs_to_pdf",
    "export_slide_to_image",
    "export_to_html",
    "export_to_images",
    "export_to_pdf",
    "print_font_warnings",
    "render_slide_to_html",
    "render_slide_to_svg",
    "run_export",
    "run_html_export",
    "run_image_export",
]
