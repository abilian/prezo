"""Screen classes for Prezo."""

from __future__ import annotations

from .blackout import BlackoutScreen
from .goto import GotoSlideScreen
from .help import HelpScreen
from .overview import SlideOverviewScreen
from .search import SlideSearchScreen
from .toc import TableOfContentsScreen

__all__ = [
    "BlackoutScreen",
    "GotoSlideScreen",
    "HelpScreen",
    "SlideOverviewScreen",
    "SlideSearchScreen",
    "TableOfContentsScreen",
]
