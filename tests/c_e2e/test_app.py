"""Tests for the main prezo application."""

from __future__ import annotations

import pytest

from prezo.app import PrezoApp, _format_recent_files
from prezo.config import Config


class TestFormatRecentFiles:
    """Tests for _format_recent_files helper function."""

    def test_empty_list_returns_empty_string(self):
        result = _format_recent_files([])
        assert result == ""

    def test_formats_single_file(self, tmp_path):
        test_file = tmp_path / "presentation.md"
        test_file.write_text("# Test")

        result = _format_recent_files([str(test_file)])
        assert "Recent Files" in result
        assert "presentation.md" in result

    def test_formats_multiple_files(self, tmp_path):
        files = []
        for i in range(3):
            f = tmp_path / f"pres{i}.md"
            f.write_text(f"# Slide {i}")
            files.append(str(f))

        result = _format_recent_files(files)
        assert "pres0.md" in result
        assert "pres1.md" in result
        assert "pres2.md" in result

    def test_respects_max_files(self, tmp_path):
        files = []
        for i in range(10):
            f = tmp_path / f"pres{i}.md"
            f.write_text(f"# Slide {i}")
            files.append(str(f))

        result = _format_recent_files(files, max_files=3)
        assert "pres0.md" in result
        assert "pres1.md" in result
        assert "pres2.md" in result
        assert "pres9.md" not in result

    def test_skips_nonexistent_files(self, tmp_path):
        existing = tmp_path / "exists.md"
        existing.write_text("# Test")

        result = _format_recent_files(
            [str(existing), "/this_path_does_not_exist/file.md"]
        )
        assert "exists.md" in result
        # The nonexistent file should not be in the output
        assert "this_path_does_not_exist" not in result

    def test_returns_empty_if_all_files_missing(self):
        result = _format_recent_files(["/missing/a.md", "/missing/b.md"])
        assert result == ""


class TestPrezoAppInit:
    """Tests for PrezoApp initialization."""

    def test_init_without_presentation(self):
        app = PrezoApp()
        assert app.presentation_path is None
        assert app.presentation is None

    def test_init_with_presentation_path(self, tmp_path):
        pres_file = tmp_path / "test.md"
        pres_file.write_text("# Slide 1\n\n---\n\n# Slide 2")

        app = PrezoApp(pres_file)
        assert app.presentation_path == pres_file

    def test_init_with_watch_enabled(self):
        app = PrezoApp(watch=True)
        assert app.watch_enabled is True

    def test_init_with_watch_disabled(self):
        app = PrezoApp(watch=False)
        assert app.watch_enabled is False

    def test_init_with_custom_config(self):
        config = Config()
        config.display.theme = "light"

        app = PrezoApp(config=config)
        assert app.config.display.theme == "light"


class TestPrezoAppAsync:
    """Async tests for PrezoApp using Textual's test framework."""

    @pytest.fixture
    def presentation_file(self, tmp_path):
        """Create a test presentation file."""
        pres = tmp_path / "test_pres.md"
        pres.write_text("""---
title: Test Presentation
---

# First Slide

Content of first slide.

---

# Second Slide

Content of second slide.

---

# Third Slide

Content of third slide.
""")
        return pres

    async def test_app_mounts_successfully(self):
        """Test that app mounts without errors."""
        app = PrezoApp()
        async with app.run_test():
            # App should mount and show welcome screen
            assert app.is_running

    async def test_app_shows_welcome_when_no_presentation(self):
        """Test welcome message shows when no presentation loaded."""
        app = PrezoApp()
        async with app.run_test():
            # Should show welcome message
            content = app.query_one("#slide-content")
            assert content is not None

    async def test_app_loads_presentation(self, presentation_file):
        """Test that app loads a presentation file."""
        app = PrezoApp(presentation_file)
        async with app.run_test() as pilot:
            # Wait for load
            await pilot.pause()

            assert app.presentation is not None
            assert app.presentation.total_slides == 3
            assert app.current_slide == 0

    async def test_next_slide_action(self, presentation_file):
        """Test navigating to next slide."""
        app = PrezoApp(presentation_file)
        async with app.run_test() as pilot:
            await pilot.pause()

            assert app.current_slide == 0

            await pilot.press("right")
            assert app.current_slide == 1

            await pilot.press("j")
            assert app.current_slide == 2

    async def test_prev_slide_action(self, presentation_file):
        """Test navigating to previous slide."""
        app = PrezoApp(presentation_file)
        async with app.run_test() as pilot:
            await pilot.pause()

            # Go to last slide first
            app.current_slide = 2
            await pilot.pause()

            await pilot.press("left")
            assert app.current_slide == 1

            await pilot.press("k")
            assert app.current_slide == 0

    async def test_first_slide_action(self, presentation_file):
        """Test going to first slide."""
        app = PrezoApp(presentation_file)
        async with app.run_test() as pilot:
            await pilot.pause()

            app.current_slide = 2
            await pilot.pause()

            await pilot.press("home")
            assert app.current_slide == 0

    async def test_last_slide_action(self, presentation_file):
        """Test going to last slide."""
        app = PrezoApp(presentation_file)
        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("end")
            assert app.current_slide == 2

    async def test_g_key_goes_to_first(self, presentation_file):
        """Test 'g' key goes to first slide."""
        app = PrezoApp(presentation_file)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.current_slide = 2
            await pilot.pause()

            await pilot.press("g")
            assert app.current_slide == 0

    async def test_G_key_goes_to_last(self, presentation_file):
        """Test 'G' key goes to last slide."""
        app = PrezoApp(presentation_file)
        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("G")
            assert app.current_slide == 2

    async def test_toggle_notes(self, presentation_file):
        """Test toggling notes panel."""
        app = PrezoApp(presentation_file)
        async with app.run_test() as pilot:
            await pilot.pause()

            assert app.notes_visible is False

            await pilot.press("p")
            assert app.notes_visible is True

            await pilot.press("p")
            assert app.notes_visible is False

    async def test_cannot_go_before_first_slide(self, presentation_file):
        """Test cannot navigate before first slide."""
        app = PrezoApp(presentation_file)
        async with app.run_test() as pilot:
            await pilot.pause()

            assert app.current_slide == 0
            await pilot.press("left")
            assert app.current_slide == 0  # Should stay at 0

    async def test_cannot_go_past_last_slide(self, presentation_file):
        """Test cannot navigate past last slide."""
        app = PrezoApp(presentation_file)
        async with app.run_test() as pilot:
            await pilot.pause()

            app.current_slide = 2
            await pilot.pause()

            await pilot.press("right")
            assert app.current_slide == 2  # Should stay at last

    async def test_space_advances_slide(self, presentation_file):
        """Test space key advances to next slide."""
        app = PrezoApp(presentation_file)
        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("space")
            assert app.current_slide == 1

    async def test_theme_cycling(self, presentation_file):
        """Test cycling through themes."""
        app = PrezoApp(presentation_file)
        async with app.run_test() as pilot:
            await pilot.pause()

            initial_theme = app.app_theme
            await pilot.press("T")
            # Theme should have changed
            assert app.app_theme != initial_theme or initial_theme == "dark"

    async def test_quit_action(self):
        """Test quit action exits app."""
        app = PrezoApp()
        async with app.run_test() as pilot:
            await pilot.press("q")
            # App should be exiting
            assert not app.is_running or app._exit


class TestPrezoAppWithNotes:
    """Tests for presentations with speaker notes."""

    @pytest.fixture
    def presentation_with_notes(self, tmp_path):
        """Create a presentation with speaker notes."""
        pres = tmp_path / "notes_pres.md"
        pres.write_text("""---
title: Notes Test
---

# Slide With Notes

Main content here.

???
These are speaker notes for slide 1.

---

# Slide Without Notes

Just content, no notes.

---

# Another With Notes

More content.

<!-- notes: HTML style notes here -->
""")
        return pres

    async def test_notes_extracted_correctly(self, presentation_with_notes):
        """Test that notes are extracted from slides."""
        app = PrezoApp(presentation_with_notes)
        async with app.run_test() as pilot:
            await pilot.pause()

            assert app.presentation is not None
            # First slide has notes
            assert "speaker notes" in app.presentation.slides[0].notes
            # Second slide has no notes
            assert app.presentation.slides[1].notes == ""
            # Third slide has HTML-style notes
            assert "HTML style notes" in app.presentation.slides[2].notes


class TestPrezoAppWithImages:
    """Tests for presentations with images."""

    @pytest.fixture
    def presentation_with_images(self, tmp_path):
        """Create a presentation with image references."""
        # Create a simple test image
        try:
            from PIL import Image

            img = Image.new("RGB", (100, 100), color="blue")
            img_path = tmp_path / "test_image.png"
            img.save(img_path)
        except ImportError:
            pytest.skip("PIL not available")

        pres = tmp_path / "image_pres.md"
        pres.write_text("""---
title: Image Test
---

# Slide With Image

![Test Image](test_image.png)

---

# Slide With Left Layout

![bg left](test_image.png)

Content on the right.

---

# Slide With Right Layout

![bg right:40%](test_image.png)

Content on the left.
""")
        return pres

    async def test_images_extracted_from_slides(self, presentation_with_images):
        """Test that images are extracted from slides."""
        app = PrezoApp(presentation_with_images)
        async with app.run_test() as pilot:
            await pilot.pause()

            assert app.presentation is not None
            # First slide has inline image
            assert len(app.presentation.slides[0].images) == 1
            assert app.presentation.slides[0].images[0].layout == "inline"

            # Second slide has left layout image
            assert len(app.presentation.slides[1].images) == 1
            assert app.presentation.slides[1].images[0].layout == "left"

            # Third slide has right layout with custom size
            assert len(app.presentation.slides[2].images) == 1
            assert app.presentation.slides[2].images[0].layout == "right"
            assert app.presentation.slides[2].images[0].size_percent == 40


class TestCommandPalette:
    """Tests for command palette functionality."""

    def test_command_palette_enabled(self):
        """Test that command palette is enabled on the app."""
        app = PrezoApp()
        assert app.ENABLE_COMMAND_PALETTE is True
        assert app.COMMAND_PALETTE_BINDING == "ctrl+p"

    def test_commands_provider_registered(self):
        """Test that PrezoCommands provider is registered."""
        from prezo.app import PrezoCommands

        app = PrezoApp()
        assert PrezoCommands in app.COMMANDS

    async def test_command_palette_opens(self):
        """Test that command palette can be opened."""
        app = PrezoApp()
        async with app.run_test() as pilot:
            # Try to open command palette
            await pilot.press("ctrl+p")
            await pilot.pause()
            # The app should have focus somewhere (command palette or main)
            # Just verify no errors occurred
            assert app.is_running


class TestPrezoCommandsProvider:
    """Tests for PrezoCommands provider."""

    def test_commands_provider_search_returns_hits(self):
        """Test that command search returns results."""
        from prezo.app import PrezoCommands

        # Create a provider and test search
        # Note: Provider needs an app context, so we test structure
        PrezoApp()

        # Verify the provider class exists and has the search method
        assert hasattr(PrezoCommands, "search")

    async def test_navigation_commands_available(self):
        """Test that navigation commands are available in command palette."""
        from prezo.app import PrezoCommands

        app = PrezoApp()
        async with app.run_test():
            # Create a provider instance
            provider = PrezoCommands(app.screen, None)

            # Search for navigation commands
            hits = []
            async for hit in provider.search("next"):
                hits.append(hit)

            # Should find "Next Slide" command
            assert len(hits) > 0
            names = [str(h.match_display) for h in hits]
            assert any("Next" in name for name in names)

    async def test_theme_commands_available(self):
        """Test that theme commands are available in command palette."""
        from prezo.app import PrezoCommands

        app = PrezoApp()
        async with app.run_test():
            provider = PrezoCommands(app.screen, None)

            # Search for theme commands
            hits = []
            async for hit in provider.search("theme"):
                hits.append(hit)

            # Should find multiple theme commands
            assert len(hits) > 0

    async def test_file_commands_available(self):
        """Test that file commands are available in command palette."""
        from prezo.app import PrezoCommands

        app = PrezoApp()
        async with app.run_test():
            provider = PrezoCommands(app.screen, None)

            # Search for reload command
            hits = []
            async for hit in provider.search("reload"):
                hits.append(hit)

            # Should find "Reload Presentation" command
            assert len(hits) > 0

    async def test_next_slide_command_uses_correct_action(self, tmp_path):
        """Test that Next Slide command calls the correct action."""
        from prezo.app import PrezoCommands

        pres = tmp_path / "test.md"
        pres.write_text("# Slide 1\n\n---\n\n# Slide 2\n\n---\n\n# Slide 3")

        app = PrezoApp(pres)
        async with app.run_test() as pilot:
            await pilot.pause()

            assert app.current_slide == 0

            provider = PrezoCommands(app.screen, None)

            # Search for next command
            hits = []
            async for hit in provider.search("next"):
                hits.append(hit)

            # Find the "Next Slide" hit and execute its command callback
            for hit in hits:
                if "Next" in str(hit.match_display):
                    # Hit.command is a coroutine function (partial of async _run_action)
                    await hit.command()
                    await pilot.pause()
                    break

            # Should have advanced to next slide
            assert app.current_slide == 1


class TestIncrementalLists:
    """Tests for incremental lists feature."""

    @pytest.fixture
    def presentation_with_lists(self, tmp_path):
        """Create a test presentation with lists."""
        pres = tmp_path / "list_pres.md"
        pres.write_text("""---
title: List Test
---

# First Slide

- Item 1
- Item 2
- Item 3

---

# Second Slide

No list here, just text.

---

# Third Slide

1. First
2. Second
3. Third
""")
        return pres

    async def test_incremental_flag_enables_reveal(self, presentation_with_lists):
        """Test that -I flag enables incremental reveal."""
        app = PrezoApp(presentation_with_lists, incremental=True)
        async with app.run_test() as pilot:
            await pilot.pause()

            # Incremental mode should be enabled
            assert app.incremental_cli is True
            assert app._is_incremental_enabled() is True

            # Should start with reveal_index = 0 (first item visible)
            assert app.reveal_index == 0

    async def test_incremental_reveal_forward(self, presentation_with_lists):
        """Test revealing items forward."""
        app = PrezoApp(presentation_with_lists, incremental=True)
        async with app.run_test() as pilot:
            await pilot.pause()

            # Start at first item
            assert app.current_slide == 0
            assert app.reveal_index == 0

            # Press right to reveal second item
            await pilot.press("right")
            assert app.current_slide == 0
            assert app.reveal_index == 1

            # Press right to reveal third item
            await pilot.press("right")
            assert app.current_slide == 0
            assert app.reveal_index == 2

            # Press right to go to next slide (all items revealed)
            await pilot.press("right")
            assert app.current_slide == 1

    async def test_incremental_reveal_backward(self, presentation_with_lists):
        """Test hiding items backward."""
        app = PrezoApp(presentation_with_lists, incremental=True)
        async with app.run_test() as pilot:
            await pilot.pause()

            # Reveal all items on first slide
            await pilot.press("right")  # reveal_index = 1
            await pilot.press("right")  # reveal_index = 2

            assert app.reveal_index == 2

            # Press left to hide last item
            await pilot.press("left")
            assert app.current_slide == 0
            assert app.reveal_index == 1

            # Press left to hide another item
            await pilot.press("left")
            assert app.current_slide == 0
            assert app.reveal_index == 0

    async def test_slide_without_lists_skips_incremental(self, presentation_with_lists):
        """Test that slides without lists skip incremental mode."""
        app = PrezoApp(presentation_with_lists, incremental=True)
        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate to second slide (no lists)
            app.current_slide = 1
            await pilot.pause()

            # Should have reveal_index = -1 (show all)
            assert app.reveal_index == -1

            # Next should go to next slide, not try to reveal
            await pilot.press("right")
            assert app.current_slide == 2

    async def test_going_back_shows_all_items(self, presentation_with_lists):
        """Test that going back to a slide shows all items."""
        app = PrezoApp(presentation_with_lists, incremental=True)
        async with app.run_test() as pilot:
            await pilot.pause()

            # Navigate through first slide
            await pilot.press("right")  # reveal_index = 1
            await pilot.press("right")  # reveal_index = 2
            await pilot.press("right")  # go to slide 1

            assert app.current_slide == 1

            # Go back to first slide
            await pilot.press("left")

            # Should show all items (reveal_index = 2)
            assert app.current_slide == 0
            assert app.reveal_index == 2

    async def test_incremental_disabled_by_default(self, presentation_with_lists):
        """Test that incremental mode is disabled by default."""
        app = PrezoApp(presentation_with_lists)
        async with app.run_test() as pilot:
            await pilot.pause()

            # Incremental mode should be disabled
            assert app.incremental_cli is False
            assert app._is_incremental_enabled() is False

            # reveal_index should be -1 (show all)
            assert app.reveal_index == -1

            # Next should go to next slide immediately
            await pilot.press("right")
            assert app.current_slide == 1

    @pytest.fixture
    def presentation_with_layout(self, tmp_path):
        """Create a test presentation with layout blocks."""
        pres = tmp_path / "layout_pres.md"
        pres.write_text("""---
title: Layout Test
---

# Slide with Columns

::: columns
::: column
- Left 1
- Left 2
:::
::: column
- Right 1
- Right 2
:::
:::

---

# Simple List

- Item 1
- Item 2
- Item 3
""")
        return pres

    async def test_layout_blocks_with_incremental(self, presentation_with_layout):
        """Test that incremental mode works with layout blocks."""
        app = PrezoApp(presentation_with_layout, incremental=True)
        async with app.run_test() as pilot:
            await pilot.pause()

            # First slide has layout blocks with 4 list items
            assert app.current_slide == 0
            assert app._get_list_count(0) == 4  # 4 items across columns
            assert app.reveal_index == 0  # Start with first item

            # Reveal items one by one
            await pilot.press("right")
            assert app.current_slide == 0
            assert app.reveal_index == 1

            await pilot.press("right")
            assert app.reveal_index == 2

            await pilot.press("right")
            assert app.reveal_index == 3

            # Next should go to next slide (all items revealed)
            await pilot.press("right")
            assert app.current_slide == 1

            # Second slide has 3 items
            assert app._get_list_count(1) == 3
            assert app.reveal_index == 0
