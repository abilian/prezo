"""Prezo - TUI Presentation Tool."""

from __future__ import annotations

import base64
import contextlib
import os
import subprocess
import sys
import tempfile
import termios
import tty
from functools import partial
from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.command import Hit, Hits, Provider
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header, Markdown, Static

from .config import Config, get_config, get_state, save_state
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
from .themes import get_next_theme, get_theme
from .widgets import ImageDisplay, StatusBar

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


class PrezoCommands(Provider):
    """Command provider for Prezo actions."""

    @property
    def _app(self) -> PrezoApp:
        """Get the app instance."""
        return self.app  # type: ignore[return-value]

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
    COMMANDS: ClassVar[set[type[Provider]]] = {PrezoCommands}  # pyright: ignore[reportIncompatibleVariableOverride]

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
        background: $surface;
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
        padding: 1 4;
    }

    #slide-content {
        width: 100%;
        padding: 1 2;
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

    /* Layout: image inline (above text) */
    #image-container.layout-inline {
        width: 100%;
    }

    #slide-image {
        width: 100%;
        height: auto;
    }

    #notes-panel {
        width: 30%;
        height: 100%;
        background: $surface-darken-1;
        border-left: solid $primary;
        padding: 1 2;
        display: none;
    }

    #notes-panel.visible {
        display: block;
    }

    #notes-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #notes-content {
        width: 100%;
    }

    #status-bar {
        width: 100%;
        height: 1;
        background: $primary;
        color: $text;
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
        Binding("T", "cycle_theme", "Theme", show=False),
        Binding("b", "blackout", "Blackout", show=False),
        Binding("w", "whiteout", "Whiteout", show=False),
        Binding("e", "edit_slide", "Edit", show=False),
        Binding("r", "reload", "Reload", show=False),
        Binding("question_mark", "show_help", "Help", show=True),
        Binding("i", "view_image", "Image", show=False),
    ]

    current_slide: reactive[int] = reactive(0)
    notes_visible: reactive[bool] = reactive(False)
    app_theme: reactive[str] = reactive("dark")

    TITLE = "Prezo"

    def __init__(
        self,
        presentation_path: str | Path | None = None,
        *,
        watch: bool | None = None,
        config: Config | None = None,
    ) -> None:
        """Initialize the Prezo application.

        Args:
            presentation_path: Path to the Markdown presentation file.
            watch: Whether to enable file watching for live reload.
            config: Optional config override. Uses global config if None.

        """
        super().__init__()
        self.config = config or get_config()
        self.state = get_state()

        self.presentation_path = Path(presentation_path) if presentation_path else None
        self.presentation: Presentation | None = None

        # Use config for watch if not explicitly set
        if watch is None:
            self.watch_enabled = self.config.behavior.auto_reload
        else:
            self.watch_enabled = watch

        self._file_mtime: float | None = None
        self._watch_timer = None
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
                            yield Markdown("", id="slide-content")
                with Vertical(id="notes-panel"):
                    yield Static("Notes", id="notes-title")
                    yield Markdown("", id="notes-content")
            yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Load presentation when app mounts."""
        # Set theme from config (must be done here, not in __init__, to avoid
        # triggering the watcher before the app has screens)
        self.app_theme = self.config.display.theme
        self.call_after_refresh(self._initial_load)

    def _initial_load(self) -> None:
        """Load presentation after UI is ready."""
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
        self.presentation = parse_presentation(self.presentation_path)

        if old_slide >= self.presentation.total_slides:
            self.current_slide = max(0, self.presentation.total_slides - 1)
        else:
            self._update_display()

        self.notify("Presentation reloaded", timeout=2)

    def load_presentation(self, path: str | Path) -> None:
        """Load a presentation from a file."""
        self.presentation_path = Path(path)
        self.presentation = parse_presentation(path)

        # Restore last position or start at 0
        abs_path = str(self.presentation_path.absolute())
        last_pos = self.state.get_position(abs_path)
        if last_pos < self.presentation.total_slides:
            self.current_slide = last_pos
        else:
            self.current_slide = 0

        self._update_display()
        self._update_progress_bar()

        if self.presentation.title:
            self.sub_title = self.presentation.title

        if self.presentation_path.exists():
            self._file_mtime = self.presentation_path.stat().st_mtime

        # Apply presentation directives on top of config
        self._apply_presentation_directives()

        # Add to recent files and save state
        self.state.add_recent_file(abs_path)
        save_state(self.state)

        # Reset timer when loading new presentation
        status_bar = self.query_one("#status-bar", StatusBar)
        self._apply_timer_config(status_bar)
        status_bar.reset_timer()

    def _apply_presentation_directives(self) -> None:
        """Apply presentation-specific directives on top of config."""
        if not self.presentation:
            return

        directives = self.presentation.directives

        # Apply theme from presentation if specified
        if directives.theme:
            self.app_theme = directives.theme

    def _apply_timer_config(self, status_bar: StatusBar) -> None:
        """Apply timer configuration to the status bar."""
        # Start with config defaults
        show_clock = self.config.timer.show_clock
        show_elapsed = self.config.timer.show_elapsed
        countdown = self.config.timer.countdown_minutes

        # Override with presentation directives if specified
        if self.presentation:
            directives = self.presentation.directives
            if directives.show_clock is not None:
                show_clock = directives.show_clock
            if directives.show_elapsed is not None:
                show_elapsed = directives.show_elapsed
            if directives.countdown_minutes is not None:
                countdown = directives.countdown_minutes

        # Apply to status bar
        status_bar.show_clock = show_clock
        status_bar.show_elapsed = show_elapsed
        status_bar.countdown_minutes = countdown
        status_bar.show_countdown = countdown > 0

    def _show_welcome(self) -> None:
        """Show welcome message when no presentation is loaded."""
        welcome = WELCOME_MESSAGE
        recent_section = _format_recent_files(self.state.recent_files)
        if recent_section:
            welcome += recent_section
        self.query_one("#slide-content", Markdown).update(welcome)
        status = self.query_one("#status-bar", StatusBar)
        status.current = 0
        status.total = 1

    def _update_display(self) -> None:
        """Update the slide display."""
        if not self.presentation or not self.presentation.slides:
            return

        slide = self.presentation.slides[self.current_slide]
        image_widget = self.query_one("#slide-image", ImageDisplay)
        image_container = self.query_one("#image-container")
        slide_container = self.query_one("#slide-container")
        horizontal_container = self.query_one("#slide-horizontal", Horizontal)

        # Reset layout classes
        image_container.remove_class(
            "visible", "layout-left", "layout-right", "layout-inline"
        )

        # Handle images - render using colored half-block characters
        if slide.images:
            # Use first image (most common case)
            first_image = slide.images[0]
            resolved_path = resolve_image_path(first_image.path, self.presentation_path)

            if resolved_path:
                image_widget.set_image(
                    resolved_path,
                    width=first_image.width,
                    height=first_image.height,
                )
                image_container.add_class("visible")

                # Apply layout based on MARP directive
                layout = first_image.layout
                if layout == "left":
                    image_container.add_class("layout-left")
                    # Ensure image is before text
                    horizontal_container.move_child(
                        image_container, before=slide_container
                    )
                elif layout == "right":
                    image_container.add_class("layout-right")
                    # Move image after text
                    horizontal_container.move_child(
                        image_container, after=slide_container
                    )
                elif layout == "inline":
                    image_container.add_class("layout-inline")
                    horizontal_container.move_child(
                        image_container, before=slide_container
                    )
                elif layout in ("background", "fit"):
                    # Background/fit images: show image full width behind/above text
                    image_container.add_class("layout-inline")
                    horizontal_container.move_child(
                        image_container, before=slide_container
                    )

                # Apply dynamic width if size_percent is specified
                default_size = 50
                has_custom_size = first_image.size_percent != default_size
                if has_custom_size and layout in ("left", "right"):
                    image_container.styles.width = f"{first_image.size_percent}%"
                else:
                    image_container.styles.width = None  # Reset to CSS default
            else:
                image_widget.clear()

        # Use cleaned content (bg images already removed by parser)
        self.query_one("#slide-content", Markdown).update(slide.content.strip())

        container = self.query_one("#slide-container", VerticalScroll)
        container.scroll_home(animate=False)

        self._update_progress_bar()
        self._update_notes()

    def _update_progress_bar(self) -> None:
        """Update the progress bar."""
        if not self.presentation:
            return

        status = self.query_one("#status-bar", StatusBar)
        status.current = self.current_slide
        status.total = self.presentation.total_slides

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

    def watch_current_slide(self, old_value: int, new_value: int) -> None:
        """React to slide changes."""
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
        """Go to the next slide."""
        if (
            self.presentation
            and self.current_slide < self.presentation.total_slides - 1
        ):
            self.current_slide += 1

    def action_prev_slide(self) -> None:
        """Go to the previous slide."""
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
        """Apply theme colors to all widgets."""
        theme = get_theme(theme_name)

        # Use Textual's dark mode as a base
        self.dark = theme_name != "light"

        # Apply theme colors via CSS variables
        self.set_class(theme_name in ("light",), "light-theme")

        # Update the app's design with theme colors
        self.styles.background = theme.background

        # Apply to slide container
        slide_container = self.query_one("#slide-container", VerticalScroll)
        slide_container.styles.background = theme.surface

        # Apply to status bar
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.styles.background = theme.primary
        status_bar.styles.color = theme.text

        # Apply to notes panel
        notes_panel = self.query_one("#notes-panel")
        notes_panel.styles.background = theme.surface
        notes_panel.styles.border_left = ("solid", theme.primary)

        notes_title = self.query_one("#notes-title", Static)
        notes_title.styles.color = theme.primary

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


def run_app(
    presentation_path: str | Path | None = None,
    *,
    watch: bool | None = None,
    config: Config | None = None,
) -> None:
    """Run the Prezo application.

    Args:
        presentation_path: Path to the presentation file.
        watch: Whether to watch for file changes. Uses config default if None.
        config: Optional config override. Uses global config if None.

    """
    app = PrezoApp(presentation_path, watch=watch, config=config)
    app.run()
