# Prezo v0.2.0 - Configuration & Images

**Status:** Complete

## Overview

Major release adding configuration system, image support, and HTML export.

## Features

### Configuration System

#### Global Configuration
- [x] Config file at `~/.config/prezo/config.toml`
- [x] `load_config()` with TOML parsing
- [x] `--config` CLI flag for custom config path

**Config structure:**
```toml
[display]
theme = "dark"                    # dark, light, dracula, solarized-dark, nord, gruvbox
syntax_theme = "monokai"          # Code block highlighting

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
```

#### Per-Presentation Directives
- [x] Parse `<!-- prezo ... -->` blocks
- [x] Override global config per-file
- [x] Supported options: theme, show_clock, show_elapsed, countdown_minutes, image_mode

**Syntax:**
```markdown
<!-- prezo
theme: light
countdown_minutes: 45
show_elapsed: true
image_mode: ascii
-->
```

#### Persistent State
- [x] Recent files list (last 20) at `~/.config/prezo/state.json`
- [x] Last slide position per file
- [x] Show recent files on welcome screen

### Image Support

#### Terminal Capability Detection
- [x] `terminal.py` module with `detect_image_capability()`
- [x] Kitty detection via `KITTY_WINDOW_ID` or `TERM`
- [x] iTerm2 detection via `TERM_PROGRAM` or `ITERM_SESSION_ID`
- [x] Sixel detection via `TERM`
- [x] `--image-mode` CLI override

#### Image Rendering Backends
- [x] **KittyRenderer** - Kitty graphics protocol
- [x] **SixelRenderer** - Sixel graphics
- [x] **ItermRenderer** - iTerm2 inline images
- [x] **AsciiRenderer** - PIL to ASCII art fallback
- [x] **ColorAsciiRenderer** - Colored ASCII art
- [x] **HalfBlockRenderer** - Unicode half-block rendering
- [x] **ChafaRenderer** - chafa CLI integration
- [x] Image caching by path + size

#### MARP Image Layouts
- [x] `![bg](path)` - Background image
- [x] `![bg left](path)` - Image on left (50%)
- [x] `![bg right](path)` - Image on right (50%)
- [x] `![bg left:40%](path)` - Custom size percentage
- [x] `![bg right:60%](path)` - Custom size percentage

### Export

#### HTML Export
- [x] `prezo -e html presentation.md`
- [x] Single HTML with embedded CSS
- [x] Slide-per-page layout with scrolling
- [x] Theme-aware styling
- [x] Optional presenter notes

### Help & Documentation
- [x] Help screen with `?` key
- [x] All keybindings displayed

## CLI Flags

```bash
# Custom config file
prezo --config /path/to/config.toml presentation.md
prezo -c myconfig.toml presentation.md

# Override image mode
prezo --image-mode ascii presentation.md
prezo --image-mode kitty presentation.md

# HTML export
prezo -e html presentation.md
prezo -e html presentation.md --theme light
prezo -e html presentation.md -o output.html
```

## Test Coverage

**68%** (334 tests)

Well-tested modules (>90%):
- `parser.py` - 97%
- `config.py` - 92%
- `terminal.py` - 97%
- `themes.py` - 96%
- `images/ascii.py` - 99%
- `images/base.py` - 100%
- `images/chafa.py` - 100%

## Dependencies

```toml
[project.dependencies]
textual = ">=0.89.1"
python-frontmatter = ">=1.1.0"

[project.optional-dependencies]
export = [
    "cairosvg>=2.7.0",
    "pypdf>=4.0.0",
]
```
