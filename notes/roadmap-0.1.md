# Prezo v0.1.0 - Initial Release

**Status:** Complete

## Overview

The initial release of Prezo - a TUI-based presentation tool for Markdown slides.

## Features

### Core Presentation Viewer
- [x] **Markdown slide parsing** - MARP/Deckset format with `---` separators
- [x] **YAML frontmatter** - Metadata extraction (title, theme)
- [x] **Keyboard navigation** - Arrow keys, j/k, space, home/end
- [x] **Slide counter** - Current/total display

### Navigation & UI
- [x] **Slide overview grid** - Press `o` for thumbnail navigation (mouse + keyboard)
- [x] **Go to slide** - Press `:` to jump to specific slide number
- [x] **Slide search** - Press `/` to search slides by content
- [x] **Table of contents** - Press `t` to navigate by headings
- [x] **Presenter notes panel** - Press `p` to toggle notes sidebar

### Editing & Live Reload
- [x] **Live reload** - Auto-refresh on file change (1s polling)
- [x] **Edit slides** - Press `e` to edit in $EDITOR, saves back to file
- [x] **MARP cleanup** - Strips bg images, directive comments, styling divs

### Display Features
- [x] **Progress bar** - Visual progress indicator with block characters
- [x] **Timer/Clock** - Current time, elapsed time, countdown (press `c` to cycle)
- [x] **Blackout/Whiteout screen** - Press `b` or `w` to blank the display
- [x] **Theme support** - Press `T` to cycle through themes

### Export
- [x] **Export to PDF** - `prezo -e pdf presentation.md`

## Themes

Available themes:
- `dark` (default)
- `light`
- `dracula`
- `solarized-dark`
- `nord`
- `gruvbox`

## Keyboard Reference

| Key | Action |
|-----|--------|
| `→` / `j` / `Space` | Next slide |
| `←` / `k` | Previous slide |
| `Home` / `g` | First slide |
| `End` / `G` | Last slide |
| `:` | Go to slide |
| `/` | Search slides |
| `o` | Slide overview |
| `t` | Table of contents |
| `p` | Toggle notes |
| `c` | Toggle clock |
| `T` | Cycle theme |
| `b` | Blackout screen |
| `w` | Whiteout screen |
| `e` | Edit current slide |
| `r` | Reload file |
| `?` | Help |
| `q` | Quit |

## Usage

```bash
# View a presentation
prezo presentation.md

# Export to PDF
prezo -e pdf presentation.md
prezo -e pdf presentation.md --theme light
prezo -e pdf presentation.md --size 100x30
prezo -e pdf presentation.md --no-chrome
prezo -e pdf presentation.md -o output.pdf
```
