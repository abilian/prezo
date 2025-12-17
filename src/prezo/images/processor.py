"""Image processing for slide content."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prezo.parser import ImageRef, Slide

    from .ascii import AsciiRenderer

# Default dimensions for rendered images
DEFAULT_IMAGE_WIDTH = 60
DEFAULT_IMAGE_HEIGHT = 15


def get_inline_renderer() -> AsciiRenderer:
    """Get a renderer suitable for inline display in markdown.

    Terminal-specific protocols (Kitty, iTerm2, Sixel, colored half-blocks)
    use ANSI escape sequences that get escaped by Textual's Markdown widget.
    For inline display, we use plain ASCII art which renders correctly.
    """
    from .ascii import AsciiRenderer

    return AsciiRenderer(detailed=True)


def resolve_image_path(image_path: str, presentation_path: Path | None) -> Path | None:
    """Resolve an image path relative to the presentation file.

    Args:
        image_path: Path as written in markdown (can be relative or absolute).
        presentation_path: Path to the presentation file.

    Returns:
        Resolved absolute path, or None if unresolvable.

    """
    # Handle URLs (not supported yet)
    if image_path.startswith(("http://", "https://", "data:")):
        return None

    path = Path(image_path)

    # If absolute, use as-is
    if path.is_absolute():
        return path if path.exists() else None

    # If relative, resolve against presentation directory
    if presentation_path:
        resolved = presentation_path.parent / path
        if resolved.exists():
            return resolved

    # Try current directory as fallback
    if path.exists():
        return path.absolute()

    return None


def render_image(
    image_ref: ImageRef,
    presentation_path: Path | None,
    *,
    width: int = DEFAULT_IMAGE_WIDTH,
    height: int = DEFAULT_IMAGE_HEIGHT,
) -> str:
    """Render a single image reference as text for inline display.

    Args:
        image_ref: The image reference to render.
        presentation_path: Path to the presentation file for relative paths.
        width: Target width in characters.
        height: Target height in lines.

    Returns:
        Rendered image as text, or a placeholder if rendering fails.

    Note:
        Always uses HalfBlockRenderer for inline display since terminal-specific
        protocols (Kitty, iTerm2, Sixel) use escape sequences that get escaped
        by Textual's Markdown widget.

    """
    resolved_path = resolve_image_path(image_ref.path, presentation_path)

    if resolved_path is None:
        # Return a placeholder for unresolvable images
        alt = image_ref.alt or "image"
        return f"[Image: {alt}]"

    renderer = get_inline_renderer()
    return renderer.render(resolved_path, width, height)


def process_slide_images(
    slide: Slide,
    presentation_path: Path | None,
    *,
    width: int = DEFAULT_IMAGE_WIDTH,
    height: int = DEFAULT_IMAGE_HEIGHT,
) -> str:
    """Process a slide's content, rendering images inline.

    Replaces markdown image syntax with rendered half-block versions.
    Uses HalfBlockRenderer which displays 2 pixels per character using
    Unicode half-block characters with true color support.

    Args:
        slide: The slide to process.
        presentation_path: Path to the presentation file.
        width: Target width for images in characters.
        height: Target height for images in lines.

    Returns:
        Slide content with images replaced by rendered versions.

    """
    if not slide.images:
        return slide.content

    # Process images in reverse order to preserve positions
    content = slide.content
    for image_ref in reversed(slide.images):
        rendered = render_image(
            image_ref,
            presentation_path,
            width=width,
            height=height,
        )

        # Wrap in code block for proper display in markdown
        wrapped = f"\n```\n{rendered}\n```\n"
        content = content[: image_ref.start] + wrapped + content[image_ref.end :]

    return content
