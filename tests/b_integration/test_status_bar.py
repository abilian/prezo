"""Tests for status bar widgets."""

from __future__ import annotations

from prezo.widgets.status_bar import (
    ClockDisplay,
    ProgressBar,
    StatusBar,
    format_progress_bar,
    format_time,
)


class TestFormatProgressBar:
    """Tests for format_progress_bar function."""

    def test_empty_progress(self):
        bar = format_progress_bar(0, 10, width=10)
        assert bar == "█░░░░░░░░░"

    def test_half_progress(self):
        bar = format_progress_bar(4, 10, width=10)
        assert bar == "█████░░░░░"

    def test_full_progress(self):
        bar = format_progress_bar(9, 10, width=10)
        assert bar == "██████████"

    def test_single_slide(self):
        bar = format_progress_bar(0, 1, width=10)
        assert bar == "██████████"

    def test_zero_total(self):
        bar = format_progress_bar(0, 0, width=10)
        assert bar == "░░░░░░░░░░"

    def test_custom_width(self):
        bar = format_progress_bar(0, 2, width=20)
        assert len(bar) == 20
        assert bar.count("█") == 10
        assert bar.count("░") == 10


class TestFormatTime:
    """Tests for format_time function."""

    def test_seconds_only(self):
        assert format_time(45) == "0:45"

    def test_minutes_and_seconds(self):
        assert format_time(125) == "2:05"

    def test_hours_minutes_seconds(self):
        assert format_time(3725) == "1:02:05"

    def test_zero(self):
        assert format_time(0) == "0:00"

    def test_negative_time(self):
        assert format_time(-125) == "-2:05"

    def test_one_hour(self):
        assert format_time(3600) == "1:00:00"

    def test_large_number_of_hours(self):
        # 10 hours, 30 minutes, 15 seconds
        assert format_time(37815) == "10:30:15"


class TestProgressBarWidget:
    """Tests for ProgressBar widget (unit tests for logic)."""

    def test_default_values(self):
        bar = ProgressBar()
        assert bar.current == 0
        assert bar.total == 1

    def test_custom_values(self):
        bar = ProgressBar(current=5, total=10)
        assert bar.current == 5
        assert bar.total == 10


class TestClockDisplayLogic:
    """Tests for ClockDisplay toggle logic (unit tests without mount)."""

    def test_default_values(self):
        clock = ClockDisplay()
        assert clock.show_clock is True
        assert clock.show_elapsed is True
        assert clock.show_countdown is False
        assert clock.countdown_minutes == 0

    def test_toggle_clock_cycle_without_countdown(self):
        """Test toggle_clock cycles correctly when no countdown is set."""
        clock = ClockDisplay()
        clock.countdown_minutes = 0

        # Initial state: clock=True, elapsed=True
        clock.show_clock = True
        clock.show_elapsed = True
        clock.show_countdown = False

        # Toggle: should turn off both since no countdown
        clock.toggle_clock()
        assert clock.show_clock is False
        assert clock.show_elapsed is False
        assert clock.show_countdown is False

        # Toggle again: should turn clock on, elapsed off
        clock.toggle_clock()
        assert clock.show_clock is True
        assert clock.show_elapsed is False

        # Toggle: should turn elapsed on
        clock.toggle_clock()
        assert clock.show_clock is True
        assert clock.show_elapsed is True

    def test_toggle_clock_cycle_with_countdown(self):
        """Test toggle_clock cycles correctly when countdown is set."""
        clock = ClockDisplay()
        clock.countdown_minutes = 30

        # Initial state: clock=True, elapsed=True
        clock.show_clock = True
        clock.show_elapsed = True
        clock.show_countdown = False

        # Toggle: should enable countdown
        clock.toggle_clock()
        assert clock.show_countdown is True
        assert clock.show_clock is True
        assert clock.show_elapsed is True

        # Toggle again: should turn everything off
        clock.toggle_clock()
        assert clock.show_clock is False
        assert clock.show_elapsed is False
        assert clock.show_countdown is False

        # Toggle: should turn clock on, elapsed off
        clock.toggle_clock()
        assert clock.show_clock is True
        assert clock.show_elapsed is False


class TestStatusBarLogic:
    """Tests for StatusBar widget logic (unit tests without mount)."""

    def test_default_values(self):
        bar = StatusBar()
        assert bar.current == 0
        assert bar.total == 1
        assert bar.show_clock is True
        assert bar.show_elapsed is True
        assert bar.show_countdown is False
        assert bar.countdown_minutes == 0

    def test_toggle_clock_same_as_clock_display(self):
        """StatusBar toggle_clock should behave like ClockDisplay."""
        bar = StatusBar()
        bar.countdown_minutes = 0

        # Set initial state
        bar.show_clock = True
        bar.show_elapsed = True
        bar.show_countdown = False

        # Toggle cycle
        bar.toggle_clock()
        assert bar.show_clock is False
        assert bar.show_elapsed is False

        bar.toggle_clock()
        assert bar.show_clock is True
        assert bar.show_elapsed is False

        bar.toggle_clock()
        assert bar.show_clock is True
        assert bar.show_elapsed is True
