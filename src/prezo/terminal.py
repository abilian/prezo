"""Terminal capability detection for Prezo."""

from __future__ import annotations

import os
import sys
from enum import Enum
from functools import lru_cache


class ImageCapability(Enum):
    """Terminal image rendering capabilities."""

    KITTY = "kitty"
    SIXEL = "sixel"
    ITERM = "iterm"
    ASCII = "ascii"
    NONE = "none"


@lru_cache(maxsize=1)
def detect_image_capability() -> ImageCapability:
    """Detect the best image rendering capability for the current terminal.

    Returns:
        The detected image capability.

    """
    # Check for Kitty terminal
    if _is_kitty():
        return ImageCapability.KITTY

    # Check for iTerm2
    if _is_iterm():
        return ImageCapability.ITERM

    # Check for Sixel support
    if _has_sixel_support():
        return ImageCapability.SIXEL

    # Fallback to ASCII
    return ImageCapability.ASCII


def _is_kitty() -> bool:
    """Check if running in Kitty terminal."""
    # KITTY_WINDOW_ID is set by Kitty
    if os.environ.get("KITTY_WINDOW_ID"):
        return True

    # Check TERM
    term = os.environ.get("TERM", "")
    return "kitty" in term.lower()


def _is_iterm() -> bool:
    """Check if running in iTerm2."""
    # iTerm2 sets these environment variables
    if os.environ.get("TERM_PROGRAM") == "iTerm.app":
        return True

    if os.environ.get("LC_TERMINAL") == "iTerm2":
        return True

    # Check for iTerm2 specific env var
    return bool(os.environ.get("ITERM_SESSION_ID"))


def _has_sixel_support() -> bool:
    """Check if terminal supports Sixel graphics.

    Note: This is a heuristic check. Proper detection would require
    querying the terminal with escape sequences.

    """
    term = os.environ.get("TERM", "")
    term_program = os.environ.get("TERM_PROGRAM", "")

    # Known Sixel-capable terminals
    sixel_terms = ["mlterm", "xterm", "mintty", "foot"]

    for t in sixel_terms:
        if t in term.lower() or t in term_program.lower():
            return True

    # Check for explicit sixel in TERM
    return "sixel" in term.lower()


def get_terminal_size() -> tuple[int, int]:
    """Get terminal size in columns and rows.

    Returns:
        Tuple of (columns, rows).

    """
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        # Fallback for non-TTY
        return 80, 24


def supports_unicode() -> bool:
    """Check if terminal supports Unicode output."""
    # Check encoding
    encoding = getattr(sys.stdout, "encoding", "") or ""
    if "utf" in encoding.lower():
        return True

    # Check LANG environment variable
    lang = os.environ.get("LANG", "")
    return "utf" in lang.lower()


def supports_true_color() -> bool:
    """Check if terminal supports 24-bit true color."""
    colorterm = os.environ.get("COLORTERM", "")
    if colorterm in ("truecolor", "24bit"):
        return True

    term = os.environ.get("TERM", "")
    if "256color" in term or "truecolor" in term:
        return True

    # iTerm2 and Kitty support true color
    return _is_iterm() or _is_kitty()


def get_capability_summary() -> dict[str, bool | int | str]:
    """Get a summary of terminal capabilities.

    Returns:
        Dictionary of capability names to values.

    """
    cols, rows = get_terminal_size()
    return {
        "image_capability": detect_image_capability().value,
        "unicode": supports_unicode(),
        "true_color": supports_true_color(),
        "columns": cols,
        "rows": rows,
        "term": os.environ.get("TERM", ""),
        "term_program": os.environ.get("TERM_PROGRAM", ""),
    }
