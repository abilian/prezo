"""Configuration management for Prezo."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Try to import tomllib (Python 3.11+) or tomli as fallback
try:
    import tomllib
except ImportError:
    import tomli as tomllib


CONFIG_DIR = Path.home() / ".config" / "prezo"
CONFIG_FILE = CONFIG_DIR / "config.toml"
STATE_FILE = CONFIG_DIR / "state.json"

DEFAULT_CONFIG_TOML = """\
# Prezo Configuration
# See https://github.com/user/prezo for documentation

[display]
theme = "dark"                    # dark, light, dracula, solarized-dark, nord, gruvbox
# syntax_theme = "monokai"        # Code block highlighting (future)

[timer]
show_clock = true
show_elapsed = true
countdown_minutes = 0             # 0 = disabled

[behavior]
auto_reload = true
reload_interval = 1.0             # seconds

[export]
default_theme = "light"
default_size = "100x30"
chrome = true

[images]
mode = "auto"                     # auto, kitty, sixel, iterm, ascii, none
ascii_width = 60
"""


@dataclass
class DisplayConfig:
    """Display configuration."""

    theme: str = "dark"
    syntax_theme: str = "monokai"


@dataclass
class TimerConfig:
    """Timer configuration."""

    show_clock: bool = True
    show_elapsed: bool = True
    countdown_minutes: int = 0


@dataclass
class BehaviorConfig:
    """Behavior configuration."""

    auto_reload: bool = True
    reload_interval: float = 1.0
    incremental_lists: bool = False  # Display lists one item at a time


@dataclass
class ExportConfig:
    """Export configuration."""

    default_theme: str = "light"
    default_size: str = "100x30"
    chrome: bool = True


@dataclass
class ImageConfig:
    """Image rendering configuration."""

    mode: str = "auto"  # auto, kitty, sixel, iterm, ascii, none
    ascii_width: int = 60


@dataclass
class Config:
    """Prezo configuration."""

    display: DisplayConfig = field(default_factory=DisplayConfig)
    timer: TimerConfig = field(default_factory=TimerConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    images: ImageConfig = field(default_factory=ImageConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create config from dictionary."""
        return cls(
            display=DisplayConfig(**data.get("display", {})),
            timer=TimerConfig(**data.get("timer", {})),
            behavior=BehaviorConfig(**data.get("behavior", {})),
            export=ExportConfig(**data.get("export", {})),
            images=ImageConfig(**data.get("images", {})),
        )

    def update_from_dict(self, data: dict[str, Any]) -> None:
        """Update config from dictionary (partial update)."""
        if "display" in data:
            for key, value in data["display"].items():
                if hasattr(self.display, key):
                    setattr(self.display, key, value)
        if "timer" in data:
            for key, value in data["timer"].items():
                if hasattr(self.timer, key):
                    setattr(self.timer, key, value)
        if "behavior" in data:
            for key, value in data["behavior"].items():
                if hasattr(self.behavior, key):
                    setattr(self.behavior, key, value)
        if "export" in data:
            for key, value in data["export"].items():
                if hasattr(self.export, key):
                    setattr(self.export, key, value)
        if "images" in data:
            for key, value in data["images"].items():
                if hasattr(self.images, key):
                    setattr(self.images, key, value)


@dataclass
class AppState:
    """Persistent application state."""

    recent_files: list[str] = field(default_factory=list)
    last_positions: dict[str, int] = field(default_factory=dict)

    def add_recent_file(self, path: str, max_files: int = 20) -> None:
        """Add a file to recent files list."""
        # Remove if already exists
        if path in self.recent_files:
            self.recent_files.remove(path)
        # Add to front
        self.recent_files.insert(0, path)
        # Trim to max
        self.recent_files = self.recent_files[:max_files]

    def set_position(self, path: str, position: int) -> None:
        """Save last position for a file."""
        self.last_positions[path] = position

    def get_position(self, path: str) -> int:
        """Get last position for a file."""
        return self.last_positions.get(path, 0)


def ensure_config_dir() -> None:
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from file.

    Args:
        config_path: Optional custom config path. Uses default if None.

    Returns:
        Loaded configuration with defaults for missing values.

    """
    config = Config()
    path = config_path or CONFIG_FILE

    if path.exists():
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            config.update_from_dict(data)
        except Exception:
            # If config is invalid, use defaults
            pass

    return config


def save_default_config() -> Path:
    """Save default configuration file.

    Returns:
        Path to the saved config file.

    """
    ensure_config_dir()
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(DEFAULT_CONFIG_TOML)
    return CONFIG_FILE


def load_state() -> AppState:
    """Load application state from file."""
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            return AppState(
                recent_files=data.get("recent_files", []),
                last_positions=data.get("last_positions", {}),
            )
        except Exception:
            pass
    return AppState()


def save_state(state: AppState) -> None:
    """Save application state to file."""
    ensure_config_dir()
    data = {
        "recent_files": state.recent_files,
        "last_positions": state.last_positions,
    }
    STATE_FILE.write_text(json.dumps(data, indent=2))


# Global config instance (loaded on first access)
_config: Config | None = None
_state: AppState | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_state() -> AppState:
    """Get the global state instance."""
    global _state
    if _state is None:
        _state = load_state()
    return _state
