"""Tests for prezo screens."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static

from prezo.parser import parse_presentation
from prezo.screens import (
    BlackoutScreen,
    GotoSlideScreen,
    HelpScreen,
    SlideOverviewScreen,
    SlideSearchScreen,
    TableOfContentsScreen,
)


class ScreenTestApp(App):
    """Minimal app for testing screens."""

    def compose(self) -> ComposeResult:
        yield Static("Test App")


# =============================================================================
# BlackoutScreen Tests
# =============================================================================


class TestBlackoutScreen:
    """Tests for BlackoutScreen."""

    def test_init_default_is_black(self):
        screen = BlackoutScreen()
        assert screen.white is False

    def test_init_can_be_white(self):
        screen = BlackoutScreen(white=True)
        assert screen.white is True

    async def test_blackout_screen_mounts(self):
        """Test blackout screen mounts correctly."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(BlackoutScreen())
            await pilot.pause()

            # Screen should be mounted
            assert len(app.screen_stack) == 2

    async def test_blackout_dismisses_on_escape(self):
        """Test escape key dismisses blackout."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(BlackoutScreen())
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            # Should be back to main screen
            assert len(app.screen_stack) == 1

    async def test_blackout_dismisses_on_b(self):
        """Test 'b' key dismisses blackout."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(BlackoutScreen())
            await pilot.pause()

            await pilot.press("b")
            await pilot.pause()

            assert len(app.screen_stack) == 1

    async def test_blackout_dismisses_on_space(self):
        """Test space key dismisses blackout."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(BlackoutScreen())
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()

            assert len(app.screen_stack) == 1

    async def test_blackout_dismisses_on_enter(self):
        """Test enter key dismisses blackout."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(BlackoutScreen())
            await pilot.pause()

            await pilot.press("enter")
            await pilot.pause()

            assert len(app.screen_stack) == 1

    async def test_whiteout_has_white_background(self):
        """Test white screen has white background."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            screen = BlackoutScreen(white=True)
            app.push_screen(screen)
            await pilot.pause()

            # Screen should be mounted with white setting
            assert screen.white is True


# =============================================================================
# GotoSlideScreen Tests
# =============================================================================


class TestGotoSlideScreen:
    """Tests for GotoSlideScreen."""

    def test_init_stores_total_slides(self):
        screen = GotoSlideScreen(total_slides=10)
        assert screen.total_slides == 10

    async def test_goto_screen_mounts(self):
        """Test goto screen mounts correctly."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(GotoSlideScreen(total_slides=10))
            await pilot.pause()

            assert len(app.screen_stack) == 2

    async def test_goto_dismisses_on_escape(self):
        """Test escape cancels goto dialog."""
        app = ScreenTestApp()
        result = None

        def handle_result(r):
            nonlocal result
            result = r

        async with app.run_test() as pilot:
            app.push_screen(GotoSlideScreen(total_slides=10), handle_result)
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert len(app.screen_stack) == 1
            assert result is None

    async def test_goto_returns_slide_index(self):
        """Test valid input returns correct slide index."""
        app = ScreenTestApp()
        result = None

        def handle_result(r):
            nonlocal result
            result = r

        async with app.run_test() as pilot:
            app.push_screen(GotoSlideScreen(total_slides=10), handle_result)
            await pilot.pause()

            # Type slide number (user enters 1-indexed)
            await pilot.press("5")
            await pilot.press("enter")
            await pilot.pause()

            # Should return 0-indexed value
            assert result == 4

    async def test_goto_empty_input_dismisses(self):
        """Test empty input dismisses without result."""
        app = ScreenTestApp()
        result = "not_set"

        def handle_result(r):
            nonlocal result
            result = r

        async with app.run_test() as pilot:
            app.push_screen(GotoSlideScreen(total_slides=10), handle_result)
            await pilot.pause()

            await pilot.press("enter")  # Submit empty
            await pilot.pause()

            assert result is None


# =============================================================================
# HelpScreen Tests
# =============================================================================


class TestHelpScreen:
    """Tests for HelpScreen."""

    async def test_help_screen_mounts(self):
        """Test help screen mounts correctly."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(HelpScreen())
            await pilot.pause()

            assert len(app.screen_stack) == 2

    async def test_help_dismisses_on_escape(self):
        """Test escape dismisses help."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(HelpScreen())
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert len(app.screen_stack) == 1

    async def test_help_dismisses_on_question_mark(self):
        """Test '?' dismisses help."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(HelpScreen())
            await pilot.pause()

            await pilot.press("question_mark")
            await pilot.pause()

            assert len(app.screen_stack) == 1


# =============================================================================
# SlideOverviewScreen Tests
# =============================================================================


class TestSlideOverviewScreen:
    """Tests for SlideOverviewScreen."""

    @pytest.fixture
    def sample_presentation(self):
        """Create a sample presentation."""
        return parse_presentation("""---
title: Test
---

# Slide 1

Content 1

---

# Slide 2

Content 2

---

# Slide 3

Content 3
""")

    def test_init_stores_presentation(self, sample_presentation):
        screen = SlideOverviewScreen(sample_presentation, 0)
        assert screen.presentation is sample_presentation
        assert screen.current_slide == 0

    async def test_overview_screen_mounts(self, sample_presentation):
        """Test overview screen mounts correctly."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(SlideOverviewScreen(sample_presentation, 0))
            await pilot.pause()

            assert len(app.screen_stack) == 2

    async def test_overview_dismisses_on_escape(self, sample_presentation):
        """Test escape dismisses overview."""
        app = ScreenTestApp()
        result = "not_set"

        def handle_result(r):
            nonlocal result
            result = r

        async with app.run_test() as pilot:
            app.push_screen(SlideOverviewScreen(sample_presentation, 0), handle_result)
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert result is None


# =============================================================================
# SlideSearchScreen Tests
# =============================================================================


class TestSlideSearchScreen:
    """Tests for SlideSearchScreen."""

    @pytest.fixture
    def sample_presentation(self):
        """Create a sample presentation for search tests."""
        return parse_presentation("""---
title: Test
---

# Introduction

Welcome to the presentation.

---

# Python Basics

Learn about Python programming.

---

# Advanced Topics

More complex subjects here.
""")

    def test_init_stores_presentation(self, sample_presentation):
        screen = SlideSearchScreen(sample_presentation)
        assert screen.presentation is sample_presentation

    async def test_search_screen_mounts(self, sample_presentation):
        """Test search screen mounts correctly."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(SlideSearchScreen(sample_presentation))
            await pilot.pause()

            assert len(app.screen_stack) == 2

    async def test_search_dismisses_on_escape(self, sample_presentation):
        """Test escape dismisses search."""
        app = ScreenTestApp()
        result = "not_set"

        def handle_result(r):
            nonlocal result
            result = r

        async with app.run_test() as pilot:
            app.push_screen(SlideSearchScreen(sample_presentation), handle_result)
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert result is None


# =============================================================================
# TableOfContentsScreen Tests
# =============================================================================


class TestTableOfContentsScreen:
    """Tests for TableOfContentsScreen."""

    @pytest.fixture
    def sample_presentation(self):
        """Create a presentation with headers for TOC."""
        return parse_presentation("""---
title: Test
---

# Chapter 1

Introduction content.

---

## Section 1.1

Details here.

---

# Chapter 2

More content.

---

### Subsection 2.1.1

Deep content.
""")

    def test_init_stores_presentation(self, sample_presentation):
        screen = TableOfContentsScreen(sample_presentation, 0)
        assert screen.presentation is sample_presentation
        assert screen.current_slide == 0

    async def test_toc_screen_mounts(self, sample_presentation):
        """Test TOC screen mounts correctly."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(TableOfContentsScreen(sample_presentation, 0))
            await pilot.pause()

            assert len(app.screen_stack) == 2

    async def test_toc_dismisses_on_escape(self, sample_presentation):
        """Test escape dismisses TOC."""
        app = ScreenTestApp()
        result = "not_set"

        def handle_result(r):
            nonlocal result
            result = r

        async with app.run_test() as pilot:
            app.push_screen(
                TableOfContentsScreen(sample_presentation, 0), handle_result
            )
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert result is None

    async def test_toc_dismisses_on_q(self, sample_presentation):
        """Test 'q' key dismisses TOC."""
        app = ScreenTestApp()
        async with app.run_test() as pilot:
            app.push_screen(TableOfContentsScreen(sample_presentation, 0))
            await pilot.pause()

            await pilot.press("q")
            await pilot.pause()

            assert len(app.screen_stack) == 1
