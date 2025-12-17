"""Status bar widgets for Prezo."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.timer import Timer


def format_progress_bar(current: int, total: int, width: int = 20) -> str:
    """Generate a progress bar string.

    Args:
        current: Current position (0-indexed)
        total: Total number of items
        width: Width of the progress bar in characters

    Returns:
        Progress bar string like "████████░░░░░░░░░░░░"

    """
    if total <= 0:
        return "░" * width

    progress = (current + 1) / total
    filled = int(progress * width)
    empty = width - filled

    return "█" * filled + "░" * empty


def format_time(seconds: int) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    if seconds < 0:
        return "-" + format_time(-seconds)

    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


class StatusBar(Static):
    """Combined status bar showing progress, clock, and elapsed time."""

    current: reactive[int] = reactive(0)
    total: reactive[int] = reactive(1)
    show_clock: reactive[bool] = reactive(True)
    show_elapsed: reactive[bool] = reactive(True)
    show_countdown: reactive[bool] = reactive(False)
    countdown_minutes: reactive[int] = reactive(0)

    def __init__(self, **kwargs) -> None:
        """Initialize the status bar."""
        super().__init__(**kwargs)
        self._start_time: datetime | None = None
        self._timer: Timer | None = None

    def on_mount(self) -> None:
        """Start the timer on mount."""
        self._start_time = datetime.now(tz=timezone.utc)
        self._timer = self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        """Timer callback to refresh the display."""
        self.refresh()

    def render(self) -> str:
        """Render the status bar content."""
        # Progress part
        bar = format_progress_bar(self.current, self.total, width=20)
        progress = f"{bar} {self.current + 1}/{self.total}"

        # Clock part
        clock_parts = []
        if self.show_clock:
            clock_parts.append(
                datetime.now(tz=timezone.utc).astimezone().strftime("%H:%M:%S"),
            )

        if self.show_elapsed and self._start_time:
            elapsed = datetime.now(tz=timezone.utc) - self._start_time
            elapsed_secs = int(elapsed.total_seconds())
            clock_parts.append(f"+{format_time(elapsed_secs)}")

        if self.show_countdown and self.countdown_minutes > 0 and self._start_time:
            total_secs = self.countdown_minutes * 60
            elapsed = datetime.now(tz=timezone.utc) - self._start_time
            remaining = total_secs - int(elapsed.total_seconds())
            clock_parts.append(f"-{format_time(remaining)}")

        clock = " │ ".join(clock_parts) if clock_parts else ""

        # Combine with spacing
        if clock:
            return f" {progress}    {clock} "
        return f" {progress} "

    def reset_timer(self) -> None:
        """Reset the elapsed timer."""
        self._start_time = datetime.now(tz=timezone.utc)
        self.refresh()

    def toggle_clock(self) -> None:
        """Cycle through clock display modes."""
        if self.show_clock and not self.show_elapsed:
            self.show_elapsed = True
        elif self.show_clock and self.show_elapsed and not self.show_countdown:
            if self.countdown_minutes > 0:
                self.show_countdown = True
            else:
                self.show_clock = False
                self.show_elapsed = False
        elif self.show_countdown:
            self.show_clock = False
            self.show_elapsed = False
            self.show_countdown = False
        else:
            self.show_clock = True
            self.show_elapsed = False

    def watch_current(self, value: int) -> None:
        """React to current slide changes."""
        self.refresh()

    def watch_total(self, value: int) -> None:
        """React to total slides changes."""
        self.refresh()

    def watch_show_clock(self, value: bool) -> None:
        """React to clock visibility changes."""
        self.refresh()

    def watch_show_elapsed(self, value: bool) -> None:
        """React to elapsed time visibility changes."""
        self.refresh()


# Keep these for backwards compatibility and separate use
class ProgressBar(Static):
    """A progress bar widget showing slide progress."""

    current: reactive[int] = reactive(0)
    total: reactive[int] = reactive(1)

    def __init__(self, current: int = 0, total: int = 1, **kwargs) -> None:
        """Initialize the progress bar.

        Args:
            current: Current slide index (0-based).
            total: Total number of slides.
            **kwargs: Additional arguments for Static widget.

        """
        super().__init__(**kwargs)
        self.current = current
        self.total = total

    def render(self) -> str:
        """Render the progress bar."""
        bar = format_progress_bar(self.current, self.total, width=30)
        return f" {bar} {self.current + 1}/{self.total} "

    def watch_current(self, value: int) -> None:
        """React to current position changes."""
        self.refresh()

    def watch_total(self, value: int) -> None:
        """React to total count changes."""
        self.refresh()


class ClockDisplay(Static):
    """A clock widget showing current time, elapsed, and countdown."""

    show_clock: reactive[bool] = reactive(True)
    show_elapsed: reactive[bool] = reactive(True)
    show_countdown: reactive[bool] = reactive(False)
    countdown_minutes: reactive[int] = reactive(0)

    def __init__(self, **kwargs) -> None:
        """Initialize the clock display."""
        super().__init__(**kwargs)
        self._start_time: datetime | None = None
        self._timer: Timer | None = None

    def on_mount(self) -> None:
        """Start the clock timer on mount."""
        self._start_time = datetime.now(tz=timezone.utc)
        self._timer = self.set_interval(1.0, self._update_time)

    def _update_time(self) -> None:
        """Timer callback to update the display."""
        self.refresh()

    def render(self) -> str:
        """Render the clock display."""
        parts = []

        if self.show_clock:
            now = datetime.now(tz=timezone.utc).astimezone()
            parts.append(now.strftime("%H:%M:%S"))

        if self.show_elapsed and self._start_time:
            elapsed = datetime.now(tz=timezone.utc) - self._start_time
            elapsed_secs = int(elapsed.total_seconds())
            parts.append(f"+{format_time(elapsed_secs)}")

        if self.show_countdown and self.countdown_minutes > 0 and self._start_time:
            total_secs = self.countdown_minutes * 60
            elapsed = datetime.now(tz=timezone.utc) - self._start_time
            remaining = total_secs - int(elapsed.total_seconds())
            parts.append(f"-{format_time(remaining)}")

        return " │ ".join(parts) if parts else ""

    def reset_timer(self) -> None:
        """Reset the elapsed timer."""
        self._start_time = datetime.now(tz=timezone.utc)
        self.refresh()

    def toggle_clock(self) -> None:
        """Cycle through clock display modes."""
        if self.show_clock and not self.show_elapsed:
            self.show_elapsed = True
        elif self.show_clock and self.show_elapsed and not self.show_countdown:
            if self.countdown_minutes > 0:
                self.show_countdown = True
            else:
                self.show_clock = False
                self.show_elapsed = False
        elif self.show_countdown:
            self.show_clock = False
            self.show_elapsed = False
            self.show_countdown = False
        else:
            self.show_clock = True
