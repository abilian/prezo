"""HTML export functionality."""

from __future__ import annotations

from pathlib import Path

from prezo.parser import clean_marp_directives, extract_notes, parse_presentation
from prezo.themes import get_theme

from .common import EXPORT_FAILED, EXPORT_SUCCESS

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
