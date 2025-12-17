# Prezo

A TUI-based presentation tool for the terminal, built with [Textual](https://textual.textualize.io/).

Display presentations written in Markdown using conventions similar to those of [MARP](https://marp.app/) or [Deckset](https://www.deckset.com/).

## Features

- **Markdown presentations** - MARP/Deckset format with `---` slide separators
- **Live reload** - Auto-refresh when file changes
- **Keyboard navigation** - Vim-style keys, arrow keys, and more
- **Slide overview** - Grid view for quick navigation (`o`)
- **Search** - Find slides by content (`/`)
- **Table of contents** - Navigate by headings (`t`)
- **Presenter notes** - Toggle notes panel (`p`)
- **Themes** - Multiple color schemes (`T` to cycle)
- **Timer/Clock** - Elapsed time and countdown (`c`)
- **Edit slides** - Open in $EDITOR (`e`)
- **PDF export** - Export with TUI appearance

## Installation

```bash
pip install prezo
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install prezo
```

## Usage

```bash
# View a presentation
prezo presentation.md

# Export to PDF
prezo -e pdf presentation.md

# Export with options
prezo -e pdf presentation.md --theme light --size 100x30 --no-chrome
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `→` / `j` / `Space` | Next slide |
| `←` / `k` | Previous slide |
| `Home` / `g` | First slide |
| `End` / `G` | Last slide |
| `:` | Go to slide number |
| `/` | Search slides |
| `o` | Slide overview |
| `t` | Table of contents |
| `p` | Toggle notes panel |
| `c` | Cycle clock display |
| `T` | Cycle theme |
| `b` | Blackout screen |
| `w` | Whiteout screen |
| `e` | Edit in $EDITOR |
| `r` | Reload file |
| `q` | Quit |

## Presentation Format

Prezo supports standard Markdown with MARP/Deckset conventions:

```markdown
---
title: My Presentation
theme: default
---

# First Slide

Content here...

---

# Second Slide

- Bullet points
- Code blocks
- Tables

???
Presenter notes go here (after ???)

---

# Third Slide

<!-- notes: Alternative notes syntax -->

More content...
```

## Themes

Available themes: `dark`, `light`, `dracula`, `solarized-dark`, `nord`, `gruvbox`

Press `T` to cycle through themes during presentation.

## Export Options

```bash
prezo -e pdf presentation.md                    # Default: 80x24, dark theme
prezo -e pdf presentation.md --theme light      # Light theme (for printing)
prezo -e pdf presentation.md --size 100x30      # Custom dimensions
prezo -e pdf presentation.md --no-chrome        # No window decorations
prezo -e pdf presentation.md -o slides.pdf      # Custom output path
```

PDF export requires optional dependencies:

```bash
pip install prezo[export]
# or
pip install cairosvg pypdf
```

## Development

```bash
# Clone and install
git clone https://github.com/user/prezo.git
cd prezo
uv sync

# Run
uv run prezo presentation.md

# Run tests
uv run pytest

# Lint
uv run ruff check .
uv run ruff format .
```

## License

MIT
