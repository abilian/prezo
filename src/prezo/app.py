"""Prezo - TUI Presentation Tool."""

from __future__ import annotations

import base64
import contextlib
import os
import re
import subprocess
import sys
import tempfile
import termios
import tty
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.color import Color
from textual.command import Hit, Hits, Provider
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header, Markdown, Static

from .config import CONFIG_DIR, Config, SessionState, get_config, get_state, save_state
from .emoji import replace_emoji
from .images.ascii import HalfBlockRenderer
from .images.chafa import chafa_available, render_with_chafa
from .images.processor import resolve_image_path
from .parser import Presentation, parse_presentation
from .screens import (
    BlackoutScreen,
    GotoSlideScreen,
    HelpScreen,
    SlideOverviewScreen,
    SlideSearchScreen,
    TableOfContentsScreen,
)
from .terminal import ImageCapability, detect_image_capability
from .themes import get_next_theme, get_theme, register_custom_themes
from .widgets import ImageDisplay, SlideContent, StatusBar

if TYPE_CHECKING:
    import types

    from textual.timer import Timer

# Optional PIL for image dimension calculations
HAS_PIL = False
PILImage: types.ModuleType | None = None  # type: ignore[possibly-undefined]
try:
    from PIL import Image as PILImage  # type: ignore[assignment]

    HAS_PIL = True
except ImportError:
    pass

WELCOME_MESSAGE = """\
# Welcome to Prezo

A TUI presentation tool.

## Usage

```
prezo <presentation.md>
```

## Navigation

| Key | Action |
|-----|--------|
| **→** / **j** / **Space** | Next slide |
| **←** / **k** | Previous slide |
| **Home** / **g** | First slide |
| **End** / **G** | Last slide |
| **:** | Go to slide |
| **/** | Search slides |
| **o** | Slide overview |
| **t** | Table of contents |
| **p** | Toggle notes |
| **c** | Toggle clock |
| **s** | Start/stop timer |
| **b** | Blackout screen |
| **e** | Edit current slide |
| **r** | Reload file |
| **Ctrl+P** | Command palette |
| **?** | Help |
| **q** | Quit |

## Features

- **Live reload**: Automatically refreshes when file changes
- **Edit slides**: Press `e` to edit in $EDITOR
- **MARP/Deckset** compatible Markdown format
"""


def _format_recent_files(recent_files: list[str], max_files: int = 5) -> str:
    """Format recent files list for display.

    Args:
        recent_files: List of recent file paths.
        max_files: Maximum number of files to show.

    Returns:
        Formatted markdown string.

    """
    if not recent_files:
        return ""

    lines = ["\n## Recent Files\n"]
    for path_str in recent_files[:max_files]:
        # Show just the filename and parent directory for brevity
        p = Path(path_str)
        if p.exists():
            display = f"{p.parent.name}/{p.name}" if p.parent.name else p.name
            lines.append(f"- `{display}`")

    if lines == ["\n## Recent Files\n"]:
        return ""

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Incremental List Helpers
# -----------------------------------------------------------------------------

# Pattern matching markdown list items (unordered and ordered)
_LIST_ITEM_PATTERN = re.compile(r"^(\s*)([-*+]|\d+\.)\s+")

# Pattern matching layout directive markers (:::)
_LAYOUT_MARKER_PATTERN = re.compile(r"^\s*:::")


def count_list_items(content: str) -> int:
    """Count the number of top-level list items in markdown content.

    Args:
        content: Markdown content to analyze.

    Returns:
        Number of top-level list items found.

    """
    count = 0
    for line in content.split("\n"):
        match = _LIST_ITEM_PATTERN.match(line)
        if match:
            # Only count top-level items (no leading whitespace)
            indent = match.group(1)
            if not indent:
                count += 1
    return count


# Braille Pattern Blank - invisible character with width, behaves like text for layout
_INVISIBLE_CHAR = "\u2800"


def _make_placeholder(text: str) -> str:
    """Create an invisible placeholder that matches the visual width of text.

    Uses Braille Pattern Blank characters which are invisible but have
    width and wrap like normal text.
    """
    return _INVISIBLE_CHAR * len(text) if text else _INVISIBLE_CHAR


def filter_list_items(content: str, max_items: int) -> str:
    """Filter content to show only the first N list items.

    Preserves layout directive markers (:::) and other structural elements.
    Hidden items are replaced with placeholder text of the same length
    to maintain visual height when text wraps.

    Args:
        content: Markdown content to filter.
        max_items: Maximum number of top-level list items to show.

    Returns:
        Filtered content with only the first N list items visible.

    """
    if max_items < 0:
        return content  # Show all

    lines = content.split("\n")
    result_lines = []
    item_count = 0
    in_hidden_item = False

    for line in lines:
        # Always preserve layout markers (:::)
        if _LAYOUT_MARKER_PATTERN.match(line):
            result_lines.append(line)
            # Reset hidden state when entering/exiting a block
            in_hidden_item = False
            continue

        match = _LIST_ITEM_PATTERN.match(line)

        if match:
            indent = match.group(1)  # Leading whitespace
            marker = match.group(2)  # List marker (-, *, +, 1.)
            text_start = match.end()
            text = line[text_start:]  # The actual text content

            if len(indent) == 0:
                # Top-level item
                item_count += 1
                if item_count <= max_items:
                    result_lines.append(line)
                    in_hidden_item = False
                else:
                    # Replace with same-length placeholder
                    placeholder = _make_placeholder(text)
                    result_lines.append(f"{indent}{marker} {placeholder}")
                    in_hidden_item = True
            elif in_hidden_item:
                # Nested item under hidden parent - also hide
                placeholder = _make_placeholder(text)
                result_lines.append(f"{indent}{marker} {placeholder}")
            else:
                # Nested item - show if parent is visible
                result_lines.append(line)
        elif in_hidden_item:
            # Content continuation of hidden item - preserve length
            stripped = line.lstrip()
            leading = line[: len(line) - len(stripped)]
            placeholder = _make_placeholder(stripped)
            result_lines.append(f"{leading}{placeholder}")
        else:
            # Non-list line (could be continuation or other content)
            result_lines.append(line)

    return "\n".join(result_lines)


class PrezoCommands(Provider):
    """Command provider for Prezo actions."""

    @property
    def _app(self) -> PrezoApp:
        """Get the app instance."""
        return cast("PrezoApp", self.app)

    async def search(self, query: str) -> Hits:
        """Search for matching commands."""
        matcher = self.matcher(query)

        # Navigation commands
        commands = [
            ("Next Slide", "next_slide", "Go to the next slide (→/j/Space)"),
            ("Previous Slide", "prev_slide", "Go to the previous slide (←/k)"),
            ("First Slide", "first_slide", "Go to the first slide (Home/g)"),
            ("Last Slide", "last_slide", "Go to the last slide (End/G)"),
            ("Go to Slide...", "goto_slide", "Jump to a specific slide number (:)"),
        ]

        # View commands
        commands.extend(
            [
                (
                    "Slide Overview",
                    "show_overview",
                    "Show grid overview of all slides (o)",
                ),
                ("Table of Contents", "show_toc", "Show table of contents (t)"),
                ("Search Slides", "search", "Search slides by content (/)"),
                ("Toggle Notes", "toggle_notes", "Show/hide presenter notes (p)"),
                ("Toggle Clock", "toggle_clock", "Cycle clock display mode (c)"),
                ("Start/Stop Timer", "toggle_timer", "Start or stop elapsed timer (S)"),
                ("Help", "show_help", "Show keyboard shortcuts (?)"),
            ]
        )

        # Theme commands
        commands.extend(
            [
                ("Cycle Theme", "cycle_theme", "Switch to next theme (T)"),
                ("Theme: Dark", "set_theme_dark", "Switch to dark theme"),
                ("Theme: Light", "set_theme_light", "Switch to light theme"),
                ("Theme: Dracula", "set_theme_dracula", "Switch to dracula theme"),
                ("Theme: Nord", "set_theme_nord", "Switch to nord theme"),
                ("Theme: Gruvbox", "set_theme_gruvbox", "Switch to gruvbox theme"),
            ]
        )

        # Screen commands
        commands.extend(
            [
                ("Blackout Screen", "blackout", "Show black screen (b)"),
                ("Whiteout Screen", "whiteout", "Show white screen (w)"),
            ]
        )

        # File commands
        commands.extend(
            [
                ("Reload Presentation", "reload", "Reload the presentation file (r)"),
                ("Edit Slide", "edit_slide", "Edit current slide in editor (e)"),
                ("Quit", "quit", "Exit Prezo (q)"),
            ]
        )

        for name, action, description in commands:
            score = matcher.match(name)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(name),
                    partial(self._run_action, action),
                    help=description,
                )

    async def _run_action(self, action: str) -> None:
        """Run an app action."""
        if action.startswith("set_theme_"):
            theme = action.replace("set_theme_", "")
            self._app.app_theme = theme
        else:
            await self._app.run_action(action)


class PrezoApp(App):
    """A TUI presentation viewer."""

    ENABLE_COMMAND_PALETTE = True
    COMMAND_PALETTE_BINDING = "ctrl+p"
    COMMANDS: ClassVar[set[type[Provider]]] = {PrezoCommands}

    CSS = """
    Screen {
        layout: vertical;
    }

    Header {
        dock: top;
    }

    Footer {
        dock: bottom;
    }

    #content-area {
        width: 100%;
        height: 1fr;
        layout: vertical;
    }

    #main-container {
        width: 100%;
        height: 1fr;
    }

    #slide-outer {
        width: 1fr;
        height: 100%;
    }

    /* Horizontal container for left/right layouts */
    #slide-horizontal {
        width: 100%;
        height: 100%;
        layout: horizontal;
    }

    /* Vertical scrolling container for content */
    #slide-container {
        width: 1fr;
        height: 100%;
        padding: 0 4 1 4;
    }

    #slide-content {
        width: 100%;
        padding: 0 2;
    }

    /* Image container - hidden by default */
    #image-container {
        height: 100%;
        padding: 1 2;
        display: none;
    }

    #image-container.visible {
        display: block;
    }

    /* Layout: image on left (default 50%) */
    #image-container.layout-left {
        width: 50%;
    }

    /* Layout: image on right (default 50%) */
    #image-container.layout-right {
        width: 50%;
    }

    /* Layout: image below text (for inline images) */
    #image-container.layout-below {
        width: 100%;
        height: 1fr;
        content-align: center middle;
    }

    /* Vertical layout mode for inline images */
    #slide-horizontal.vertical-layout {
        layout: vertical;
    }

    /* In vertical layout, text takes only needed height */
    #slide-horizontal.vertical-layout #slide-container {
        height: auto;
        padding-bottom: 0;
    }

    /* Adjust padding for image when below text */
    #image-container.layout-below {
        padding-top: 0;
        padding-bottom: 1;
    }

    #slide-image {
        width: 100%;
        height: auto;
    }

    #notes-panel {
        width: 30%;
        height: 100%;
        border-left: solid white;
        padding: 1 2;
        display: none;
    }

    #notes-panel.visible {
        display: block;
    }

    #notes-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #notes-content {
        width: 100%;
    }

    #status-bar {
        width: 100%;
        height: 1;
        text-align: center;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit"),
        Binding("right", "next_slide", "Next", show=True),
        Binding("left", "prev_slide", "Previous", show=True),
        Binding("j", "next_slide", "Next", show=False),
        Binding("k", "prev_slide", "Previous", show=False),
        Binding("space", "next_slide", "Next", show=False),
        Binding("home", "first_slide", "First"),
        Binding("end", "last_slide", "Last"),
        Binding("g", "first_slide", "First", show=False),
        Binding("G", "last_slide", "Last", show=False),
        Binding("o", "show_overview", "Overview", show=True),
        Binding("colon", "goto_slide", "Go to", show=False),
        Binding("slash", "search", "Search", show=True),
        Binding("t", "show_toc", "TOC", show=True),
        Binding("p", "toggle_notes", "Notes", show=True),
        Binding("c", "toggle_clock", "Clock", show=False),
        Binding("s", "toggle_timer", "Timer", show=False),
        Binding("S", "toggle_timer", "Timer", show=False),
        Binding("T", "cycle_theme", "Theme", show=False),
        Binding("b", "blackout", "Blackout", show=False),
        Binding("w", "whiteout", "Whiteout", show=False),
        Binding("e", "edit_slide", "Edit", show=False),
        Binding("r", "reload", "Reload", show=False),
        Binding("question_mark", "show_help", "Help", show=True),
        Binding("i", "view_image", "Image", show=False),
        Binding("tab", "enter_link_mode", "Links", show=False, priority=True),
    ]

    current_slide: reactive[int] = reactive(0)
    notes_visible: reactive[bool] = reactive(False)
    app_theme: reactive[str] = reactive("dark")
    reveal_index: reactive[int] = reactive(-1)  # -1 = show all, 0+ = show up to index
    link_mode: reactive[bool] = reactive(False)  # True when navigating links
    current_link: reactive[int] = reactive(-1)  # Current link index (-1 = none)

    TITLE = "Prezo"

    def __init__(
        self,
        presentation_path: str | Path | None = None,
        *,
        watch: bool | None = None,
        config: Config | None = None,
        incremental: bool = False,
        time_budget: int | None = None,
        resume: bool = False,
    ) -> None:
        """Initialize the Prezo application.

        Args:
            presentation_path: Path to the Markdown presentation file.
            watch: Whether to enable file watching for live reload.
            config: Optional config override. Uses global config if None.
            incremental: Whether to display lists incrementally (-I flag).
            time_budget: Time budget in minutes for pacing indicator.
            resume: Whether to resume from last session state.

        """
        super().__init__()
        self.config = config or get_config()
        self.state = get_state()

        # Register custom themes from config
        register_custom_themes(self.config)

        # Load custom CSS if specified
        self._custom_css_paths = self._find_custom_css_paths(presentation_path)

        self.presentation_path = Path(presentation_path) if presentation_path else None
        self.presentation: Presentation | None = None

        # Incremental lists: CLI flag overrides config
        self.incremental_cli = incremental

        # Time budget: CLI flag overrides config/presentation directives
        self.time_budget_cli = time_budget

        # Resume from last session
        self.resume_session = resume

        # Use config for watch if not explicitly set
        if watch is None:
            self.watch_enabled = self.config.behavior.auto_reload
        else:
            self.watch_enabled = watch

        self._file_mtime: float | None = None
        self._watch_timer: Timer | None = None
        self._reload_interval = self.config.behavior.reload_interval

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        with Vertical(id="content-area"):
            with Horizontal(id="main-container"):
                with Vertical(id="slide-outer"):
                    with Horizontal(id="slide-horizontal"):
                        # Image container (left position) - hidden by default
                        with Vertical(id="image-container"):
                            yield ImageDisplay(id="slide-image")
                        # Text container
                        with VerticalScroll(id="slide-container"):
                            yield SlideContent("", id="slide-content")
                with Vertical(id="notes-panel"):
                    yield Static("Notes", id="notes-title")
                    yield Markdown("", id="notes-content")
            yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Load presentation when app mounts."""
        # Load custom CSS files
        self._load_custom_css()

        # Set theme from config (must be done here, not in __init__, to avoid
        # triggering the watcher before the app has screens)
        self.app_theme = self.config.display.theme
        self.call_after_refresh(self._initial_load)

    def _find_custom_css_paths(
        self, presentation_path: str | Path | None
    ) -> list[Path]:
        """Find custom CSS files to load.

        Searches for CSS files in order of priority (highest last):
        1. Global config CSS (~/.config/prezo/custom.tcss)
        2. Config-specified CSS (display.custom_css)
        3. Local project CSS (./prezo.tcss, next to presentation)

        Args:
            presentation_path: Path to the presentation file.

        Returns:
            List of CSS paths to load, in priority order.

        """
        paths = []

        # Global custom CSS
        global_css = CONFIG_DIR / "custom.tcss"
        if global_css.exists():
            paths.append(global_css)

        # Config-specified CSS
        if self.config.display.custom_css:
            config_css = Path(self.config.display.custom_css).expanduser()
            if config_css.exists() and config_css not in paths:
                paths.append(config_css)

        # Local project CSS (next to presentation)
        if presentation_path:
            pres_path = Path(presentation_path)
            local_css = pres_path.parent / "prezo.tcss"
            if local_css.exists() and local_css not in paths:
                paths.append(local_css)

        return paths

    def _load_custom_css(self) -> None:
        """Load custom CSS files into the app's stylesheet."""
        for css_path in self._custom_css_paths:
            try:
                css_content = css_path.read_text()
                self.stylesheet.add_source(
                    css_content,
                    read_from=(str(css_path), str(css_path)),
                    is_default_css=False,
                )
            except Exception:
                # Silently skip invalid CSS files
                pass

    def _initial_load(self) -> None:
        """Load presentation after UI is ready."""
        # Apply theme now that widgets are ready
        self._apply_theme(self.app_theme)

        if self.presentation_path:
            self.load_presentation(self.presentation_path)
            if self.watch_enabled:
                self._start_file_watch()
        else:
            self._show_welcome()

    def _start_file_watch(self) -> None:
        """Start watching the file for changes."""
        if self.presentation_path and self.presentation_path.exists():
            self._file_mtime = self.presentation_path.stat().st_mtime
            self._watch_timer = self.set_interval(
                self._reload_interval, self._check_file_changes
            )

    def _check_file_changes(self) -> None:
        """Check if the presentation file has changed."""
        if not self.presentation_path or not self.presentation_path.exists():
            return

        current_mtime = self.presentation_path.stat().st_mtime
        if self._file_mtime and current_mtime > self._file_mtime:
            self._file_mtime = current_mtime
            self._reload_presentation()

    def _reload_presentation(self) -> None:
        """Reload the presentation from disk."""
        if not self.presentation_path:
            return

        old_slide = self.current_slide
        old_reveal = self.reveal_index
        self.presentation = parse_presentation(self.presentation_path)

        if old_slide >= self.presentation.total_slides:
            target_slide = max(0, self.presentation.total_slides - 1)
            self._init_reveal_for_slide(target_slide, show_all=False)
            self.current_slide = target_slide
        else:
            # Preserve reveal position if still valid
            list_count = self._get_list_count(old_slide)
            if self._is_incremental_enabled(old_slide) and list_count > 0:
                self.reveal_index = max(0, min(old_reveal, list_count - 1))
            else:
                self.reveal_index = -1
            self._update_display()

        self.notify("Presentation reloaded", timeout=2)

    def load_presentation(self, path: str | Path) -> None:
        """Load a presentation from a file."""
        self.presentation_path = Path(path)
        self.presentation = parse_presentation(path)
        abs_path = str(self.presentation_path.absolute())

        # Check for session state to restore
        session = self.state.get_session(abs_path) if self.resume_session else None

        if session:
            # Restore from session
            target_slide = min(session.slide, self.presentation.total_slides - 1)
        else:
            # Restore last position or start at 0
            last_pos = self.state.get_position(abs_path)
            target_slide = last_pos if last_pos < self.presentation.total_slides else 0

        # Set the slide - the watcher will initialize reveal state
        if self.current_slide == target_slide:
            # Watcher won't fire, so initialize manually
            self._init_reveal_for_slide(target_slide, show_all=False)
            self._update_display()
        else:
            self.current_slide = target_slide

        self._update_progress_bar()

        if self.presentation.title:
            self.sub_title = self.presentation.title

        if self.presentation_path.exists():
            self._file_mtime = self.presentation_path.stat().st_mtime

        # Apply presentation directives on top of config (but not theme if resuming)
        self._apply_presentation_directives(skip_theme=session is not None)

        # Restore theme from session AFTER directives (session has priority)
        if session and session.theme:
            self.app_theme = session.theme

        # Add to recent files and save state
        self.state.add_recent_file(abs_path)
        save_state(self.state)

        # Setup timer
        status_bar = self.query_one("#status-bar", StatusBar)
        self._apply_timer_config(status_bar)

        if session:
            # Restore timer state from session
            status_bar._elapsed_when_paused = session.elapsed_seconds
            status_bar.timer_running = session.timer_running
            if session.timer_running:
                status_bar._start_time = datetime.now(tz=timezone.utc)
            self.notify("Session restored", timeout=2)
        else:
            status_bar.reset_timer()

    def _is_incremental_enabled(self, slide_index: int | None = None) -> bool:
        """Check if incremental mode is enabled for a slide.

        Priority: per-slide directive > CLI flag > config > presentation directive

        Args:
            slide_index: Slide index to check. Uses current_slide if None.

        Returns:
            True if incremental lists should be enabled.

        """
        if not self.presentation or not self.presentation.slides:
            return False

        idx = slide_index if slide_index is not None else self.current_slide
        if idx < 0 or idx >= len(self.presentation.slides):
            return False

        slide = self.presentation.slides[idx]

        # Per-slide directive takes highest priority
        if slide.incremental is not None:
            return slide.incremental

        # CLI flag overrides config and presentation directives
        if self.incremental_cli:
            return True

        # Presentation directive (from <!-- prezo --> block)
        if self.presentation.directives.incremental_lists is not None:
            return self.presentation.directives.incremental_lists

        # Fall back to config
        return self.config.behavior.incremental_lists

    def _get_list_count(self, slide_index: int | None = None) -> int:
        """Get the number of top-level list items in a slide.

        Args:
            slide_index: Slide index to check. Uses current_slide if None.

        Returns:
            Number of top-level list items.

        """
        if not self.presentation or not self.presentation.slides:
            return 0

        idx = slide_index if slide_index is not None else self.current_slide
        if idx < 0 or idx >= len(self.presentation.slides):
            return 0

        slide = self.presentation.slides[idx]
        return count_list_items(slide.content)

    def _init_reveal_for_slide(
        self, slide_index: int, *, show_all: bool = False
    ) -> None:
        """Initialize reveal state for a specific slide.

        Args:
            slide_index: The slide to initialize for.
            show_all: If True, reveal all items. If False, start with first item.

        """
        if self._is_incremental_enabled(slide_index):
            list_count = self._get_list_count(slide_index)
            if list_count > 0:
                self.reveal_index = (list_count - 1) if show_all else 0
            else:
                self.reveal_index = -1  # No list items, show all content
        else:
            self.reveal_index = -1  # Incremental disabled, show all

    def _apply_presentation_directives(self, *, skip_theme: bool = False) -> None:
        """Apply presentation-specific directives on top of config.

        Args:
            skip_theme: If True, don't apply theme directive (used when resuming session).

        """
        if not self.presentation:
            return

        directives = self.presentation.directives

        # Apply theme from presentation if specified (unless skipped for session resume)
        if directives.theme and not skip_theme:
            self.app_theme = directives.theme

    def _apply_timer_config(self, status_bar: StatusBar) -> None:
        """Apply timer configuration to the status bar."""
        # Start with config defaults
        show_clock = self.config.timer.show_clock
        show_elapsed = self.config.timer.show_elapsed
        countdown = self.config.timer.countdown_minutes
        time_budget = self.config.timer.time_budget_minutes

        # Override with presentation directives if specified
        if self.presentation:
            directives = self.presentation.directives
            if directives.show_clock is not None:
                show_clock = directives.show_clock
            if directives.show_elapsed is not None:
                show_elapsed = directives.show_elapsed
            if directives.countdown_minutes is not None:
                countdown = directives.countdown_minutes
            if directives.time_budget_minutes is not None:
                time_budget = directives.time_budget_minutes

        # CLI flag takes highest priority for time budget
        if self.time_budget_cli is not None:
            time_budget = self.time_budget_cli

        # Apply to status bar
        status_bar.show_clock = show_clock
        status_bar.show_elapsed = show_elapsed
        status_bar.countdown_minutes = countdown
        status_bar.show_countdown = countdown > 0
        status_bar.time_budget_minutes = time_budget

    def _show_welcome(self) -> None:
        """Show welcome message when no presentation is loaded."""
        welcome = WELCOME_MESSAGE
        recent_section = _format_recent_files(self.state.recent_files)
        if recent_section:
            welcome += recent_section
        self.query_one("#slide-content", SlideContent).set_content(welcome)
        status = self.query_one("#status-bar", StatusBar)
        status.current = 0
        status.total = 1

    def _update_display(self) -> None:
        """Update the slide display."""
        if not self.presentation or not self.presentation.slides:
            return

        slide = self.presentation.slides[self.current_slide]

        # Handle image display
        self._update_image_display(slide)

        # Use cleaned content (bg images already removed by parser)
        content = slide.content.strip()

        # Rewrite emoji to ASCII markers on terminals that misrender them
        if not self.config.display.emoji:
            content = replace_emoji(content)

        # Apply incremental filtering if enabled
        if self._is_incremental_enabled() and self.reveal_index >= 0:
            content = filter_list_items(content, self.reveal_index + 1)

        self.query_one("#slide-content", SlideContent).set_content(content)

        container = self.query_one("#slide-container", VerticalScroll)
        container.scroll_home(animate=False)

        self._update_progress_bar()
        self._update_notes()

    def _update_image_display(self, slide) -> None:
        """Update the image display for a slide."""
        image_widget = self.query_one("#slide-image", ImageDisplay)
        image_container = self.query_one("#image-container")
        slide_container = self.query_one("#slide-container")
        horizontal_container = self.query_one("#slide-horizontal", Horizontal)

        # Reset layout classes
        image_container.remove_class(
            "visible", "layout-left", "layout-right", "layout-below"
        )
        horizontal_container.remove_class("vertical-layout")

        if not slide.images:
            return

        # Use first image (most common case)
        first_image = slide.images[0]
        resolved_path = resolve_image_path(first_image.path, self.presentation_path)

        if not resolved_path:
            image_widget.clear()
            return

        # Set the image
        image_widget.set_image(
            resolved_path,
            width=first_image.width,
            height=first_image.height,
        )
        image_container.add_class("visible")

        # Apply layout and positioning
        self._apply_image_layout(
            first_image,
            resolved_path,
            image_container,
            slide_container,
            horizontal_container,
        )

    def _apply_image_layout(
        self,
        image,
        resolved_path: Path,
        image_container,
        slide_container,
        horizontal_container,
    ) -> None:
        """Apply layout classes and width for an image."""
        # Calculate width for fit_vertical mode
        container_width_percent = None
        if image.fit_vertical and image.layout in ("left", "right"):
            calculated_width = self._calculate_fit_width(resolved_path, image_container)
            if calculated_width:
                container_width_percent = calculated_width

        # Apply layout based on MARP directive
        match image.layout:
            case "left":
                image_container.add_class("layout-left")
                horizontal_container.move_child(image_container, before=slide_container)
            case "right":
                image_container.add_class("layout-right")
                horizontal_container.move_child(image_container, after=slide_container)
            case "inline" | "background" | "fit":
                image_container.add_class("layout-below")
                horizontal_container.add_class("vertical-layout")
                horizontal_container.move_child(image_container, after=slide_container)

        # Apply dynamic width
        if container_width_percent is not None:
            image_container.styles.width = f"{container_width_percent}%"
        elif image.size_percent != 50 and image.layout in ("left", "right"):
            image_container.styles.width = f"{image.size_percent}%"
        else:
            image_container.styles.width = None

    def _update_progress_bar(self) -> None:
        """Update the progress bar and reveal indicator."""
        if not self.presentation:
            return

        status = self.query_one("#status-bar", StatusBar)
        status.current = self.current_slide
        status.total = self.presentation.total_slides

        # Update reveal indicator
        if self._is_incremental_enabled():
            list_count = self._get_list_count()
            if list_count > 0 and self.reveal_index >= 0:
                status.reveal_current = self.reveal_index
                status.reveal_total = list_count
            else:
                status.reveal_current = -1
                status.reveal_total = 0
        else:
            status.reveal_current = -1
            status.reveal_total = 0

    def _update_notes(self) -> None:
        """Update the notes panel content."""
        if not self.presentation or not self.presentation.slides:
            return

        slide = self.presentation.slides[self.current_slide]
        notes_content = self.query_one("#notes-content", Markdown)

        if slide.notes:
            notes_content.update(slide.notes)
        else:
            notes_content.update("*No notes for this slide*")

    def _calculate_fit_width(self, image_path: Path, container) -> int | None:
        """Calculate container width percentage for fit_vertical mode.

        Calculates the width needed for an image to fill the available height
        while maintaining its aspect ratio.

        Args:
            image_path: Path to the image file.
            container: The container widget for height reference.

        Returns:
            Width as percentage of total width, or None if calculation fails.

        """
        if not HAS_PIL:
            return None

        try:
            # Get image dimensions
            with PILImage.open(image_path) as img:
                img_width, img_height = img.size

            if img_height == 0:
                return None

            # Get terminal dimensions
            term_width = self.size.width
            term_height = self.size.height

            # Account for UI elements (header, footer, status bar, padding)
            # Approximate available height for content
            available_height = term_height - 6  # header + footer + status + padding

            # Terminal cells are typically ~2:1 (height:width in pixels)
            # A cell is roughly twice as tall as it is wide
            cell_aspect_ratio = 2.0

            # Image aspect ratio (width/height)
            img_aspect = img_width / img_height

            # Calculate width in cells needed to fill available_height
            # If image fills available_height rows, each row shows (img_height/available_height) pixels
            # Width in cells = (img_width / (img_height/available_height)) / cell_aspect_ratio
            # Simplified: width_cells = available_height * img_aspect / cell_aspect_ratio
            width_cells = available_height * img_aspect / cell_aspect_ratio

            # Convert to percentage of terminal width
            width_percent = int((width_cells / term_width) * 100)

            # Clamp to reasonable range (10% to 80%)
            return max(10, min(80, width_percent))

        except Exception:
            return None

    def watch_current_slide(self, old_value: int, new_value: int) -> None:
        """React to slide changes."""
        # Exit link mode when changing slides
        if self.link_mode:
            self._exit_link_mode()
        # Determine direction and initialize reveal state appropriately
        going_back = new_value < old_value
        self._init_reveal_for_slide(new_value, show_all=going_back)
        self._update_display()
        self._save_position()

    def _save_position(self) -> None:
        """Save current position to state."""
        if self.presentation_path:
            abs_path = str(self.presentation_path.absolute())
            self.state.set_position(abs_path, self.current_slide)
            save_state(self.state)

    def watch_notes_visible(self, visible: bool) -> None:
        """React to notes panel visibility changes."""
        notes_panel = self.query_one("#notes-panel")
        if visible:
            notes_panel.add_class("visible")
        else:
            notes_panel.remove_class("visible")

    def action_next_slide(self) -> None:
        """Go to the next slide or reveal next list item."""
        if not self.presentation:
            return

        # Check if we should reveal next item instead of advancing slide
        if self._is_incremental_enabled():
            list_count = self._get_list_count()
            if (
                list_count > 0
                and self.reveal_index >= 0
                and self.reveal_index < list_count - 1
            ):
                self.reveal_index += 1
                self._update_display()
                self._update_progress_bar()
                return

        # No more items to reveal, go to next slide
        if self.current_slide < self.presentation.total_slides - 1:
            # The watcher will initialize reveal_index for the new slide
            self.current_slide += 1

    def action_prev_slide(self) -> None:
        """Go to the previous slide or hide last revealed item."""
        if not self.presentation:
            return

        # Check if we should hide last item instead of going back
        if self._is_incremental_enabled() and self.reveal_index > 0:
            self.reveal_index -= 1
            self._update_display()
            self._update_progress_bar()
            return

        # Go to previous slide (watcher will show all items)
        if self.current_slide > 0:
            self.current_slide -= 1

    def action_first_slide(self) -> None:
        """Go to the first slide."""
        self.current_slide = 0

    def action_last_slide(self) -> None:
        """Go to the last slide."""
        if self.presentation:
            self.current_slide = self.presentation.total_slides - 1

    def action_show_overview(self) -> None:
        """Show the slide overview grid."""
        if not self.presentation:
            return

        def handle_overview_result(slide_index: int | None) -> None:
            if slide_index is not None:
                self.current_slide = slide_index

        self.push_screen(
            SlideOverviewScreen(self.presentation, self.current_slide),
            handle_overview_result,
        )

    def action_goto_slide(self) -> None:
        """Show go-to-slide dialog."""
        if not self.presentation:
            return

        def handle_goto_result(slide_index: int | None) -> None:
            if slide_index is not None:
                self.current_slide = slide_index

        self.push_screen(
            GotoSlideScreen(self.presentation.total_slides),
            handle_goto_result,
        )

    def action_search(self) -> None:
        """Show slide search dialog."""
        if not self.presentation:
            return

        def handle_search_result(slide_index: int | None) -> None:
            if slide_index is not None:
                self.current_slide = slide_index

        self.push_screen(
            SlideSearchScreen(self.presentation),
            handle_search_result,
        )

    def action_show_toc(self) -> None:
        """Show table of contents."""
        if not self.presentation:
            return

        def handle_toc_result(slide_index: int | None) -> None:
            if slide_index is not None:
                self.current_slide = slide_index

        self.push_screen(
            TableOfContentsScreen(self.presentation, self.current_slide),
            handle_toc_result,
        )

    def action_toggle_notes(self) -> None:
        """Toggle the notes panel visibility."""
        self.notes_visible = not self.notes_visible

    def action_toggle_clock(self) -> None:
        """Cycle through clock display modes."""
        self.query_one("#status-bar", StatusBar).toggle_clock()

    def action_toggle_timer(self) -> None:
        """Start or stop the elapsed timer."""
        self.query_one("#status-bar", StatusBar).toggle_timer()

    def action_cycle_theme(self) -> None:
        """Cycle through available themes."""
        self.app_theme = get_next_theme(self.app_theme)

    def action_show_help(self) -> None:
        """Show the help screen."""
        self.push_screen(HelpScreen())

    def watch_app_theme(self, theme_name: str) -> None:
        """Apply theme when it changes."""
        # Only apply to widgets after mount (watcher fires during init)
        if not self.is_mounted:
            return
        self._apply_theme(theme_name)
        self.notify(f"Theme: {theme_name}", timeout=1)

    def _apply_theme(self, theme_name: str) -> None:
        """Apply theme colors to all widgets by re-rendering everything."""
        theme = get_theme(theme_name)

        # Parse colors once
        bg_color = Color.parse(theme.background)
        surface_color = Color.parse(theme.surface)
        primary_color = Color.parse(theme.primary)
        text_color = Color.parse(theme.text)

        # Update the app's design with theme colors
        self.styles.background = bg_color

        # Apply to screen
        self.screen.styles.background = bg_color

        # Apply to all containers with parsed Color objects
        for widget_id in [
            "#content-area",
            "#main-container",
            "#slide-outer",
            "#slide-horizontal",
            "#slide-container",
            "#image-container",
        ]:
            widget = self.query_one(widget_id)
            widget.styles.background = surface_color

        # Apply to status bar
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.styles.background = primary_color
        status_bar.styles.color = text_color

        # Apply to notes panel
        notes_panel = self.query_one("#notes-panel")
        notes_panel.styles.background = surface_color
        notes_panel.styles.border_left = ("solid", primary_color)

        notes_title = self.query_one("#notes-title", Static)
        notes_title.styles.color = primary_color

        # Apply to slide content widget
        slide_content = self.query_one("#slide-content", SlideContent)
        slide_content.styles.background = surface_color
        slide_content.styles.color = text_color

        # Force complete re-render of slide content
        self._update_display()

        # Force complete repaint
        self.refresh(repaint=True, layout=True)

    def action_blackout(self) -> None:
        """Show blackout screen."""
        self.push_screen(BlackoutScreen(white=False))

    def action_whiteout(self) -> None:
        """Show whiteout screen."""
        self.push_screen(BlackoutScreen(white=True))

    def action_reload(self) -> None:
        """Manually reload the presentation."""
        if self.presentation_path:
            self._reload_presentation()
        else:
            self.notify("No presentation file to reload", severity="warning")

    def _save_session(self) -> None:
        """Save current session state for later resume."""
        if not self.presentation_path:
            return

        abs_path = str(self.presentation_path.absolute())
        status_bar = self.query_one("#status-bar", StatusBar)

        # Get current elapsed time
        elapsed = status_bar._get_elapsed_seconds()

        session = SessionState(
            slide=self.current_slide,
            elapsed_seconds=float(elapsed),
            timer_running=status_bar.timer_running,
            theme=self.app_theme,  # Always save current theme
        )

        self.state.save_session(abs_path, session)
        save_state(self.state)

    async def action_quit(self) -> None:
        """Save session and quit the application."""
        self._save_session()
        self.exit()

    def action_view_image(self) -> None:
        """View current slide's image in native quality (suspend mode)."""
        if not self.presentation or not self.presentation.slides:
            return

        slide = self.presentation.slides[self.current_slide]
        if not slide.images:
            self.notify("No image on this slide", timeout=2)
            return

        # Get the resolved image path
        first_image = slide.images[0]
        resolved_path = resolve_image_path(first_image.path, self.presentation_path)
        if not resolved_path or not resolved_path.exists():
            self.notify("Image not found", severity="warning")
            return

        # View image in suspend mode using native protocol
        self._view_image_native(resolved_path)

    def _view_image_native(self, image_path: Path) -> None:
        """Display image using native terminal protocol in suspend mode."""
        capability = detect_image_capability()

        with self.suspend():
            # Clear screen
            sys.stdout.write("\x1b[2J\x1b[H")

            # Get terminal size
            try:
                size = os.get_terminal_size()
                width, height = size.columns, size.lines - 2
            except OSError:
                width, height = 80, 24

            # Show image based on capability
            if capability == ImageCapability.ITERM:
                self._show_iterm_image(image_path, width, height)
            elif capability == ImageCapability.KITTY:
                self._show_kitty_image(image_path, width, height)
            else:
                # Fall back to chafa or half-block in suspend mode
                self._show_fallback_image(image_path, width, height)

            # Show instructions
            print(f"\n\nImage: {image_path.name}")
            print("Press any key to return...")

            # Wait for keypress
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _show_iterm_image(self, path: Path, width: int, height: int) -> None:
        """Show image using iTerm2 protocol."""
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")

        name_b64 = base64.b64encode(path.name.encode()).decode("ascii")
        size = path.stat().st_size

        params = (
            f"name={name_b64};size={size};width={width};height={height};"
            f"inline=1;preserveAspectRatio=1"
        )
        sys.stdout.write(f"\x1b]1337;File={params}:{data}\x07")
        sys.stdout.flush()

    def _show_kitty_image(self, path: Path, width: int, height: int) -> None:
        """Show image using Kitty protocol."""
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")

        # Kitty protocol with chunked transmission
        chunk_size = 4096
        chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

        for i, chunk in enumerate(chunks):
            is_last = i == len(chunks) - 1
            m = 0 if is_last else 1
            if i == 0:
                sys.stdout.write(
                    f"\x1b_Ga=T,f=100,c={width},r={height},m={m};{chunk}\x1b\\"
                )
            else:
                sys.stdout.write(f"\x1b_Gm={m};{chunk}\x1b\\")

        sys.stdout.flush()

    def _show_fallback_image(self, path: Path, width: int, height: int) -> None:
        """Show image using chafa or half-block."""
        if chafa_available():
            result = render_with_chafa(path, width, height)
            if result:
                print(result)
                return

        renderer = HalfBlockRenderer()
        print(renderer.render(path, width, height))

    def action_edit_slide(self) -> None:
        """Edit the current slide in an external editor."""
        if not self.presentation or not self.presentation.source_path:
            self.notify("No presentation file to edit", severity="warning")
            return

        slide = self.presentation.slides[self.current_slide]
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "vi"))

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            prefix=f"slide_{self.current_slide + 1}_",
            delete=False,
        ) as f:
            f.write(slide.raw_content)
            temp_path = f.name

        try:
            with self.suspend():
                subprocess.run([editor, temp_path], check=True)

            edited_content = Path(temp_path).read_text()

            if edited_content != slide.raw_content:
                self.presentation.update_slide(self.current_slide, edited_content)
                self.notify("Slide saved", timeout=2)
                self._reload_presentation()
            else:
                self.notify("No changes made", timeout=2)

        except subprocess.CalledProcessError:
            self.notify("Editor exited with error", severity="error")
        except Exception as e:
            self.notify(f"Edit failed: {e}", severity="error")
        finally:
            with contextlib.suppress(OSError):
                os.unlink(temp_path)

    # -------------------------------------------------------------------------
    # Link Navigation
    # -------------------------------------------------------------------------

    def _get_current_slide_links(self) -> list:
        """Get links from the current slide."""
        if not self.presentation or not self.presentation.slides:
            return []
        slide = self.presentation.slides[self.current_slide]
        return slide.links

    def action_enter_link_mode(self) -> None:
        """Enter link navigation mode (L)."""
        links = self._get_current_slide_links()
        if not links:
            self.notify("No links on this slide", timeout=2)
            return

        if self.link_mode:
            # Already in link mode - exit
            self._exit_link_mode()
        else:
            # Enter link mode, select first link
            self.link_mode = True
            self.current_link = 0
            self._update_link_indicator()

    def on_click(self, event) -> None:
        """Handle clicks, including on links."""
        # Check if clicked on a link (Rich style with link attribute)
        if event.style and event.style.link:
            url = event.style.link
            self._open_link(url)
            event.stop()

    def on_key(self, event) -> None:
        """Handle key presses, especially in link mode."""
        if not self.link_mode:
            return  # Let normal bindings handle it

        links = self._get_current_slide_links()
        if not links:
            return

        key = event.key

        if key in ("j", "down", "right", "tab"):
            # Next link
            self.current_link = (self.current_link + 1) % len(links)
            self._update_link_indicator()
            event.prevent_default()
            event.stop()
        elif key in ("k", "up", "left", "shift+tab"):
            # Previous link
            self.current_link = (self.current_link - 1) % len(links)
            self._update_link_indicator()
            event.prevent_default()
            event.stop()
        elif key in ("enter", "o"):
            # Open link
            link = links[self.current_link]
            self._open_link(link.url)
            self._exit_link_mode()
            event.prevent_default()
            event.stop()
        elif key in ("escape", "q", "l"):
            # Exit link mode
            self._exit_link_mode()
            event.prevent_default()
            event.stop()

    def _exit_link_mode(self) -> None:
        """Exit link mode and clear indicator."""
        self.link_mode = False
        self.current_link = -1
        self._update_link_indicator()

    def _update_link_indicator(self) -> None:
        """Update status bar with current link info."""
        status = self.query_one("#status-bar", StatusBar)
        links = self._get_current_slide_links()

        if self.link_mode and links and self.current_link >= 0:
            link = links[self.current_link]
            # Truncate text if too long
            text = link.text[:40] + "..." if len(link.text) > 40 else link.text
            url = link.url[:30] + "..." if len(link.url) > 30 else link.url
            status.link_info = (
                f'Link {self.current_link + 1}/{len(links)}: "{text}" → {url}'
            )
        else:
            status.link_info = ""

    def _open_link(self, url: str) -> None:
        """Open a link with the system default application."""
        # Determine if it's a local file and resolve the path
        resolved_path: Path | None = None

        if url.startswith("file://"):
            resolved_path = Path(url[7:])
        elif not url.startswith(("http://", "https://", "mailto:")):
            resolved_path = resolve_image_path(url, self.presentation_path)
            if resolved_path is None:
                self.notify(f"File not found: {url}", severity="error")
                return

        # Open with system default
        try:
            if resolved_path is not None:
                self._open_local_file(resolved_path)
                display_url = str(resolved_path)
            else:
                self._open_url(url)
                display_url = url

            self.notify(f"Opening: {display_url}", timeout=2)
        except Exception as e:
            self.notify(f"Failed to open link: {e}", severity="error")

    def _open_local_file(self, path: Path) -> None:
        """Open a local file with the system default application."""
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        elif sys.platform == "win32":
            os.startfile(str(path))
        else:
            subprocess.run(["xdg-open", str(path)], check=True)

    def _open_url(self, url: str) -> None:
        """Open a URL with the system default browser."""
        if sys.platform == "darwin":
            subprocess.run(["open", url], check=True)
        elif sys.platform == "win32":
            os.startfile(url)
        else:
            subprocess.run(["xdg-open", url], check=True)


def run_app(
    presentation_path: str | Path | None = None,
    *,
    watch: bool | None = None,
    config: Config | None = None,
    incremental: bool = False,
    time_budget: int | None = None,
    resume: bool = False,
) -> None:
    """Run the Prezo application.

    Args:
        presentation_path: Path to the presentation file.
        watch: Whether to watch for file changes. Uses config default if None.
        config: Optional config override. Uses global config if None.
        incremental: Whether to display lists incrementally (-I flag).
        time_budget: Time budget in minutes for pacing indicator.
        resume: Whether to resume from last session state.

    """
    app = PrezoApp(
        presentation_path,
        watch=watch,
        config=config,
        incremental=incremental,
        time_budget=time_budget,
        resume=resume,
    )
    app.run()
