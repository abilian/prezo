"""Integration tests for config file I/O operations."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from prezo.config import AppState, load_config


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
