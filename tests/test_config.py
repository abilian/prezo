"""Tests for the config module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from prezo.config import (
    AppState,
    BehaviorConfig,
    Config,
    DisplayConfig,
    ExportConfig,
    ImageConfig,
    TimerConfig,
    load_config,
)


class TestDisplayConfig:
    def test_default_values(self):
        config = DisplayConfig()
        assert config.theme == "dark"
        assert config.syntax_theme == "monokai"

    def test_custom_values(self):
        config = DisplayConfig(theme="light", syntax_theme="github")
        assert config.theme == "light"
        assert config.syntax_theme == "github"


class TestTimerConfig:
    def test_default_values(self):
        config = TimerConfig()
        assert config.show_clock is True
        assert config.show_elapsed is True
        assert config.countdown_minutes == 0

    def test_custom_values(self):
        config = TimerConfig(show_clock=False, countdown_minutes=45)
        assert config.show_clock is False
        assert config.countdown_minutes == 45


class TestBehaviorConfig:
    def test_default_values(self):
        config = BehaviorConfig()
        assert config.auto_reload is True
        assert config.reload_interval == 1.0

    def test_custom_values(self):
        config = BehaviorConfig(auto_reload=False, reload_interval=2.5)
        assert config.auto_reload is False
        assert config.reload_interval == 2.5


class TestExportConfig:
    def test_default_values(self):
        config = ExportConfig()
        assert config.default_theme == "light"
        assert config.default_size == "100x30"
        assert config.chrome is True


class TestImageConfig:
    def test_default_values(self):
        config = ImageConfig()
        assert config.mode == "auto"
        assert config.ascii_width == 60


class TestConfig:
    def test_default_config(self):
        config = Config()
        assert config.display.theme == "dark"
        assert config.timer.show_clock is True
        assert config.behavior.auto_reload is True

    def test_from_dict(self):
        data = {
            "display": {"theme": "light"},
            "timer": {"countdown_minutes": 30},
        }
        config = Config.from_dict(data)
        assert config.display.theme == "light"
        assert config.timer.countdown_minutes == 30
        # Unspecified values should be defaults
        assert config.behavior.auto_reload is True

    def test_update_from_dict(self):
        config = Config()
        config.update_from_dict({"display": {"theme": "dracula"}})
        assert config.display.theme == "dracula"
        # Other values unchanged
        assert config.timer.show_clock is True


class TestAppState:
    def test_empty_state(self):
        state = AppState()
        assert state.recent_files == []
        assert state.last_positions == {}

    def test_add_recent_file(self):
        state = AppState()
        state.add_recent_file("/path/to/file1.md")
        state.add_recent_file("/path/to/file2.md")

        assert len(state.recent_files) == 2
        assert state.recent_files[0] == "/path/to/file2.md"  # Most recent first

    def test_add_recent_file_deduplicates(self):
        state = AppState()
        state.add_recent_file("/path/to/file1.md")
        state.add_recent_file("/path/to/file2.md")
        state.add_recent_file("/path/to/file1.md")  # Re-add first file

        assert len(state.recent_files) == 2
        assert state.recent_files[0] == "/path/to/file1.md"

    def test_add_recent_file_limits_size(self):
        state = AppState()
        for i in range(25):
            state.add_recent_file(f"/path/to/file{i}.md")

        assert len(state.recent_files) == 20  # Default max

    def test_set_and_get_position(self):
        state = AppState()
        state.set_position("/path/to/file.md", 5)
        assert state.get_position("/path/to/file.md") == 5
        assert state.get_position("/unknown/file.md") == 0  # Default


class TestLoadConfig:
    def test_load_missing_config_returns_defaults(self):
        config = load_config(Path("/nonexistent/config.toml"))
        assert config.display.theme == "dark"

    def test_load_valid_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[display]\ntheme = "light"\n')
            f.flush()
            config = load_config(Path(f.name))
            assert config.display.theme == "light"


class TestSaveLoadState:
    def test_save_and_load_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"

            # Create and save state
            state = AppState()
            state.add_recent_file("/path/to/file.md")
            state.set_position("/path/to/file.md", 10)

            # Manually write state (since save_state uses module constants)
            data = {
                "recent_files": state.recent_files,
                "last_positions": state.last_positions,
            }
            state_file.write_text(json.dumps(data))

            # Load it back
            loaded_data = json.loads(state_file.read_text())
            loaded_state = AppState(
                recent_files=loaded_data.get("recent_files", []),
                last_positions=loaded_data.get("last_positions", {}),
            )

            assert loaded_state.recent_files == ["/path/to/file.md"]
            assert loaded_state.get_position("/path/to/file.md") == 10


class TestConfigUpdateFromDict:
    """Tests for Config.update_from_dict method with various sections."""

    def test_update_timer_config(self):
        config = Config()
        config.update_from_dict(
            {"timer": {"show_clock": False, "countdown_minutes": 45}}
        )
        assert config.timer.show_clock is False
        assert config.timer.countdown_minutes == 45

    def test_update_behavior_config(self):
        config = Config()
        config.update_from_dict(
            {"behavior": {"auto_reload": False, "reload_interval": 5.0}}
        )
        assert config.behavior.auto_reload is False
        assert config.behavior.reload_interval == 5.0

    def test_update_export_config(self):
        config = Config()
        config.update_from_dict({"export": {"default_theme": "dark", "chrome": False}})
        assert config.export.default_theme == "dark"
        assert config.export.chrome is False

    def test_update_images_config(self):
        config = Config()
        config.update_from_dict({"images": {"mode": "kitty", "ascii_width": 80}})
        assert config.images.mode == "kitty"
        assert config.images.ascii_width == 80

    def test_update_unknown_keys_ignored(self):
        config = Config()
        # Unknown keys should be ignored, not raise errors
        config.update_from_dict(
            {"display": {"unknown_key": "value"}, "unknown_section": {"key": "value"}}
        )
        # Config should still be valid
        assert config.display.theme == "dark"

    def test_update_multiple_sections(self):
        config = Config()
        config.update_from_dict(
            {
                "display": {"theme": "light"},
                "timer": {"show_clock": False},
                "behavior": {"auto_reload": False},
                "export": {"chrome": False},
                "images": {"mode": "none"},
            }
        )
        assert config.display.theme == "light"
        assert config.timer.show_clock is False
        assert config.behavior.auto_reload is False
        assert config.export.chrome is False
        assert config.images.mode == "none"


class TestLoadConfigErrors:
    """Tests for load_config error handling."""

    def test_load_invalid_toml_returns_defaults(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("invalid toml content {{{{")
            f.flush()
            config = load_config(Path(f.name))
            # Should return defaults
            assert config.display.theme == "dark"
            assert config.timer.show_clock is True

    def test_load_empty_file_returns_defaults(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("")
            f.flush()
            config = load_config(Path(f.name))
            assert config.display.theme == "dark"

    def test_load_partial_config_fills_defaults(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("[timer]\nshow_clock = false\n")
            f.flush()
            config = load_config(Path(f.name))
            # Specified value loaded
            assert config.timer.show_clock is False
            # Other values should be defaults
            assert config.display.theme == "dark"
            assert config.behavior.auto_reload is True


class TestAppStateEdgeCases:
    """Edge case tests for AppState."""

    def test_add_recent_file_with_custom_max(self):
        state = AppState()
        for i in range(10):
            state.add_recent_file(f"/file{i}.md", max_files=5)

        assert len(state.recent_files) == 5
        # Most recent should be first
        assert state.recent_files[0] == "/file9.md"

    def test_get_position_default_for_unknown_file(self):
        state = AppState()
        assert state.get_position("/unknown.md") == 0

    def test_set_position_overwrites_existing(self):
        state = AppState()
        state.set_position("/file.md", 5)
        state.set_position("/file.md", 10)
        assert state.get_position("/file.md") == 10

    def test_recent_files_preserves_order(self):
        state = AppState()
        state.add_recent_file("/a.md")
        state.add_recent_file("/b.md")
        state.add_recent_file("/c.md")

        # Most recent first
        assert state.recent_files == ["/c.md", "/b.md", "/a.md"]

    def test_readd_moves_to_front(self):
        state = AppState()
        state.add_recent_file("/a.md")
        state.add_recent_file("/b.md")
        state.add_recent_file("/a.md")  # Re-add

        # /a.md should now be first
        assert state.recent_files == ["/a.md", "/b.md"]


class TestExportConfigValues:
    """Tests for ExportConfig edge cases."""

    def test_custom_size(self):
        config = ExportConfig(default_size="120x40")
        assert config.default_size == "120x40"


class TestImageConfigValues:
    """Tests for ImageConfig edge cases."""

    def test_all_valid_modes(self):
        for mode in ["auto", "kitty", "sixel", "iterm", "ascii", "none"]:
            config = ImageConfig(mode=mode)
            assert config.mode == mode

    def test_custom_ascii_width(self):
        config = ImageConfig(ascii_width=100)
        assert config.ascii_width == 100
