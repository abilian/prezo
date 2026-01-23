"""Parse MARP/Deckset-style Markdown presentations."""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter

# -----------------------------------------------------------------------------
# Data Types (Nouns)
# -----------------------------------------------------------------------------


@dataclass
class ImageRef:
    """Reference to an image in a slide."""

    alt: str  # Alt text
    path: str  # Path as written in markdown
    start: int  # Start position in content
    end: int  # End position in content
    # MARP-style layout directives
    layout: str = "inline"  # "inline", "left", "right", "background", "fit"
    size_percent: int = 50  # Size percentage for left/right layouts
    # MARP-style size directives (in characters for TUI, or percentage)
    width: int | None = None  # Width in characters (None = auto)
    height: int | None = None  # Height in characters (None = auto)


@dataclass
class Slide:
    """A single slide in the presentation."""

    content: str  # Cleaned content for display
    index: int
    raw_content: str = ""  # Original content for editing
    notes: str = ""
    images: list[ImageRef] = field(default_factory=list)
    incremental: bool | None = None  # Per-slide override for incremental lists


@dataclass
class PresentationConfig:
    """Prezo-specific configuration from presentation directives."""

    theme: str | None = None
    show_clock: bool | None = None
    show_elapsed: bool | None = None
    countdown_minutes: int | None = None
    image_mode: str | None = None
    incremental_lists: bool | None = None

    def merge_to_dict(self) -> dict[str, Any]:
        """Convert non-None values to a config dict for merging."""
        result: dict[str, Any] = {}
        if self.theme is not None:
            result.setdefault("display", {})["theme"] = self.theme
        if self.show_clock is not None:
            result.setdefault("timer", {})["show_clock"] = self.show_clock
        if self.show_elapsed is not None:
            result.setdefault("timer", {})["show_elapsed"] = self.show_elapsed
        if self.countdown_minutes is not None:
            result.setdefault("timer", {})["countdown_minutes"] = self.countdown_minutes
        if self.image_mode is not None:
            result.setdefault("images", {})["mode"] = self.image_mode
        if self.incremental_lists is not None:
            result.setdefault("behavior", {})["incremental_lists"] = (
                self.incremental_lists
            )
        return result


@dataclass
class Presentation:
    """A parsed presentation with metadata and slides."""

    slides: list[Slide] = field(default_factory=list)
    title: str = ""
    theme: str = "default"
    metadata: dict = field(default_factory=dict)
    source_path: Path | None = None
    directives: PresentationConfig = field(default_factory=PresentationConfig)
    _raw_frontmatter: str = ""  # Original frontmatter text for reconstruction

    @property
    def total_slides(self) -> int:
        """Return the total number of slides in the presentation."""
        return len(self.slides)

    def update_slide(self, index: int, new_content: str) -> None:
        """Update a slide's content and save to source file."""
        if not self.source_path:
            msg = "Cannot save: no source file path"
            raise ValueError(msg)
        if not 0 <= index < len(self.slides):
            msg = f"Invalid slide index: {index}"
            raise ValueError(msg)

        slide_content, _notes = extract_notes(new_content)
        self.slides[index].raw_content = new_content
        self.slides[index].content = clean_marp_directives(slide_content).strip()

        save_presentation(self)


# -----------------------------------------------------------------------------
# Main Public API (Verbs)
# -----------------------------------------------------------------------------


def parse_presentation(source: str | Path) -> Presentation:
    """Parse a Markdown presentation from a file path or string.

    Supports MARP/Deckset conventions:
    - YAML frontmatter for metadata
    - `---` to separate slides
    - `???` or `<!-- notes -->` for presenter notes (optional)
    """
    source_path, text = _read_source(source)
    return _parse_content(text, source_path)


def save_presentation(presentation: Presentation) -> None:
    """Save presentation to its source file."""
    if not presentation.source_path:
        return

    content = _reconstruct_content(presentation)
    presentation.source_path.write_text(content)


# -----------------------------------------------------------------------------
# Pure Parsing Functions (Functional Core)
# -----------------------------------------------------------------------------


def split_slides(content: str) -> list[str]:
    """Split content by slide separators (---).

    Handles MARP/Deckset convention where --- on its own line separates slides.
    """
    parts = re.split(r"\n---\s*\n", content)
    slides = [p for p in parts if p.strip()]
    return slides if slides else [""]


def extract_notes(content: str) -> tuple[str, str]:
    """Extract presenter notes from slide content.

    Supports:
    - `???` separator (Remark.js style)
    - `<!-- notes: ... -->` HTML comments

    Returns:
        Tuple of (content_without_notes, notes)

    """
    if "\n???" in content:
        parts = content.split("\n???", 1)
        return parts[0], parts[1] if len(parts) > 1 else ""

    match = re.search(
        r"<!--\s*notes?:\s*(.*?)\s*-->",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        notes = match.group(1)
        content = content[: match.start()] + content[match.end() :]
        return content, notes

    return content, ""


def extract_slide_incremental(content: str) -> bool | None:
    """Extract per-slide incremental directive from content.

    Looks for:
    - <!-- incremental --> to enable incremental lists for this slide
    - <!-- no-incremental --> to disable incremental lists for this slide

    Returns:
        True if incremental enabled, False if disabled, None if not specified.

    """
    if re.search(r"<!--\s*incremental\s*-->", content, re.IGNORECASE):
        return True
    if re.search(r"<!--\s*no-incremental\s*-->", content, re.IGNORECASE):
        return False
    return None


def extract_prezo_directives(content: str) -> PresentationConfig:
    """Extract Prezo-specific directives from presentation content.

    Looks for HTML comment blocks in the format:
    <!-- prezo
    theme: dark
    show_clock: true
    countdown_minutes: 45
    -->

    Returns:
        PresentationConfig with parsed directive values.

    """
    config = PresentationConfig()

    # Look for prezo directive block
    pattern = r"<!--\s*prezo\s+(.*?)-->"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

    if not match:
        return config

    directive_text = match.group(1)

    # Parse key: value pairs
    for line in directive_text.strip().split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue

        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        # Parse known directives
        if key == "theme":
            config.theme = value
        elif key in ("show_clock", "showclock"):
            config.show_clock = value.lower() in ("true", "1", "yes", "on")
        elif key in ("show_elapsed", "showelapsed"):
            config.show_elapsed = value.lower() in ("true", "1", "yes", "on")
        elif key in ("countdown_minutes", "countdown", "countdownminutes"):
            with contextlib.suppress(ValueError):
                config.countdown_minutes = int(value)
        elif key in ("image_mode", "imagemode", "images"):
            config.image_mode = value
        elif key in ("incremental_lists", "incremental", "incrementallists"):
            config.incremental_lists = value.lower() in ("true", "1", "yes", "on")

    return config


def extract_images(content: str) -> list[ImageRef]:
    """Extract markdown image references from content.

    Handles both standard markdown images and MARP background images:
    - ![alt](path) - inline image
    - ![bg](path) - background image
    - ![bg left](path) - image on left side
    - ![bg right](path) - image on right side
    - ![bg left:40%](path) - image on left with specific size
    - ![bg fit](path) - fit image to container

    Args:
        content: Slide content to search.

    Returns:
        List of ImageRef objects for each image found.

    """
    images = []

    # Match all markdown images: ![...](path)
    pattern = r"!\[([^\]]*)\]\(([^)]+)\)"

    for match in re.finditer(pattern, content):
        alt_text = match.group(1)
        path = match.group(2)

        # Parse MARP directives from alt text
        directives = _parse_marp_image_directive(alt_text)

        # Extract clean alt text (remove bg directives and size specs)
        clean_alt = re.sub(r"^bg\s*", "", alt_text).strip()
        layout_pattern = r"^(left|right|fit|contain|cover)(\s*:\s*\d+%)?"
        clean_alt = re.sub(layout_pattern, "", clean_alt).strip()
        # Remove size directives from alt text
        clean_alt = re.sub(
            r"(?:^|\s)(?:w|width|h|height)\s*:\s*\d+", "", clean_alt
        ).strip()

        images.append(
            ImageRef(
                alt=clean_alt,
                path=path,
                start=match.start(),
                end=match.end(),
                layout=directives.layout,
                size_percent=directives.size_percent,
                width=directives.width,
                height=directives.height,
            )
        )

    return images


@dataclass
class _ImageDirectives:
    """Parsed MARP image directives."""

    layout: str = "inline"
    size_percent: int = 50
    width: int | None = None
    height: int | None = None


def _parse_marp_image_directive(alt_text: str) -> _ImageDirectives:
    """Parse MARP image directive from alt text.

    Supports:
    - ![bg](path) - background
    - ![bg left](path) - left layout
    - ![bg right:40%](path) - right layout with size
    - ![w:50](path) or ![width:50](path) - width in characters
    - ![h:20](path) or ![height:20](path) - height in characters
    - Combined: ![bg left w:40 h:20](path)

    Args:
        alt_text: The alt text from ![alt](path)

    Returns:
        _ImageDirectives with parsed values.

    """
    result = _ImageDirectives()
    alt_lower = alt_text.lower().strip()

    # Parse width directive: w:N or width:N
    width_match = re.search(r"(?:^|\s)(?:w|width)\s*:\s*(\d+)", alt_lower)
    if width_match:
        result.width = int(width_match.group(1))

    # Parse height directive: h:N or height:N
    height_match = re.search(r"(?:^|\s)(?:h|height)\s*:\s*(\d+)", alt_lower)
    if height_match:
        result.height = int(height_match.group(1))

    # Not a background image - return with default inline layout
    if not alt_lower.startswith("bg"):
        return result

    # Parse the directive after "bg"
    directive = alt_lower[2:].strip()

    # Parse layout from directive
    if not directive or directive.startswith(("w:", "width:", "h:", "height:")):
        # Default background
        result.layout = "background"
        result.size_percent = 100
    elif left_match := re.match(r"left(?:\s*:\s*(\d+)%)?", directive):
        result.layout = "left"
        result.size_percent = int(left_match.group(1)) if left_match.group(1) else 50
    elif right_match := re.match(r"right(?:\s*:\s*(\d+)%)?", directive):
        result.layout = "right"
        result.size_percent = int(right_match.group(1)) if right_match.group(1) else 50
    elif directive.startswith(("fit", "contain")):
        result.layout = "fit"
        result.size_percent = 100
    else:
        # Cover or unknown directive - treat as background
        result.layout = "background"
        result.size_percent = 100

    return result


def clean_marp_directives(content: str, *, keep_divs: bool = False) -> str:
    """Remove MARP-specific directives that don't render in TUI.

    Cleans up:
    - MARP HTML comments (<!-- _class: ... -->, <!-- _header: ... -->, etc.)
    - MARP image directives (![bg ...])
    - Empty HTML divs with only styling
    - All HTML divs (unless keep_divs=True for HTML export)

    Args:
        content: Slide content to clean.
        keep_divs: If True, preserve structural divs (for HTML export).

    """
    # Remove MARP directive comments
    content = re.sub(r"<!--\s*_\w+:.*?-->\s*\n?", "", content)

    # Remove MARP background image syntax (keep regular images)
    content = re.sub(r"!\[bg[^\]]*\]\([^)]+\)\s*\n?", "", content)

    # Remove empty divs with only style attributes
    content = re.sub(r'<div[^>]*style="[^"]*"[^>]*>\s*</div>\s*\n?', "", content)

    if not keep_divs:
        # Remove inline HTML divs (keep the content) - for TUI display
        content = re.sub(r"<div[^>]*>\s*\n?", "", content)
        content = re.sub(r"\s*</div>", "", content)

    # Clean up multiple blank lines
    return re.sub(r"\n{3,}", "\n\n", content)


# -----------------------------------------------------------------------------
# Private Implementation (Imperative Shell)
# -----------------------------------------------------------------------------


def _read_source(source: str | Path) -> tuple[Path | None, str]:
    """Read presentation source, handling both file paths and raw strings."""
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).exists()):
        source_path = Path(source)
        return source_path, source_path.read_text()
    return None, source


def _parse_content(text: str, source_path: Path | None) -> Presentation:
    """Parse presentation content (pure logic, no I/O)."""
    post = frontmatter.loads(text)
    metadata = dict(post.metadata)

    raw_frontmatter = _extract_raw_frontmatter(text, metadata)
    title = str(metadata.get("title") or metadata.get("header", ""))
    theme = str(metadata.get("theme", "default"))

    # Extract Prezo-specific directives from content
    directives = extract_prezo_directives(post.content)

    # Override theme from directives if specified
    if directives.theme:
        theme = directives.theme

    presentation = Presentation(
        title=title,
        theme=theme,
        metadata=metadata,
        source_path=source_path,
        _raw_frontmatter=raw_frontmatter,
        directives=directives,
    )

    for i, raw_slide in enumerate(split_slides(post.content)):
        slide_content, notes = extract_notes(raw_slide)
        # Extract images BEFORE cleaning (clean_marp_directives removes bg images)
        images = extract_images(slide_content)
        # Extract per-slide incremental setting
        incremental = extract_slide_incremental(slide_content)
        cleaned_content = clean_marp_directives(slide_content).strip()
        slide = Slide(
            content=cleaned_content,
            index=i,
            raw_content=raw_slide,
            notes=notes.strip(),
            images=images,
            incremental=incremental,
        )
        presentation.slides.append(slide)

    return presentation


def _extract_raw_frontmatter(text: str, metadata: dict) -> str:
    """Extract raw frontmatter text for reconstruction."""
    if not metadata or not text.startswith("---"):
        return ""

    end_idx = text.find("\n---\n", 3)
    if end_idx != -1:
        return text[: end_idx + 5]  # Include closing ---\n
    return ""


def _reconstruct_content(presentation: Presentation) -> str:
    """Reconstruct presentation file content from slides."""
    parts = []

    if presentation._raw_frontmatter:
        parts.append(presentation._raw_frontmatter)

    for i, slide in enumerate(presentation.slides):
        if i > 0:
            parts.append("\n---\n")
        parts.append(slide.raw_content)

    content = "".join(parts)
    if not content.endswith("\n"):
        content += "\n"

    return content
