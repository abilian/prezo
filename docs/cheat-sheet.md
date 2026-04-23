# Prezo Cheat Sheet

Quick reference for Prezo - terminal-based Markdown presentations.

## Keyboard Shortcuts

### Navigation

| Key | Action |
|-----|--------|
| `Right` / `Space` / `j` | Next slide (or next item in incremental mode) |
| `Left` / `k` | Previous slide |
| `Home` / `g` | First slide |
| `End` / `G` | Last slide |
| `:` | Go to slide number |
| `/` | Search slides |

### Views

| Key | Action |
|-----|--------|
| `o` | Slide overview grid |
| `t` | Table of contents |
| `p` | Toggle presenter notes |
| `i` | View current image (native quality) |

### Display

| Key | Action |
|-----|--------|
| `T` | Cycle theme |
| `c` | Toggle clock/timer |
| `s` | Start/stop timer |
| `b` | Blackout screen |
| `w` | Whiteout screen |

### Links

| Key | Action |
|-----|--------|
| `Tab` | Enter link navigation mode |
| `j` / `k` | Next / previous link (in link mode) |
| `Enter` / `o` | Open selected link |
| `Escape` | Exit link mode |

Markdown links are also clickable with the mouse. URLs open in the browser; local file paths open with the system default application.

### Other

| Key | Action |
|-----|--------|
| `e` | Edit slide in $EDITOR |
| `r` | Reload presentation |
| `Ctrl+P` | Command palette |
| `?` | Help |
| `q` | Quit |

## Command Line

```bash
# Basic usage
prezo presentation.md
prezo -v                                 # Show version

# With options
prezo presentation.md --theme dracula    # Set theme
prezo presentation.md --no-watch         # Disable auto-reload
prezo presentation.md -I                 # Incremental lists
prezo presentation.md --image-mode kitty # Image mode
prezo presentation.md --time-budget 30   # Pacing indicator (30 min)
prezo presentation.md --resume           # Resume last session

# Export
prezo presentation.md -e pdf             # Export to PDF
prezo presentation.md -e html            # Export to HTML
prezo presentation.md -e png             # Export to PNG
prezo presentation.md -e svg             # Export to SVG

# Export options
prezo presentation.md -e pdf --theme light
prezo presentation.md -e pdf --size 100x30
prezo presentation.md -e pdf --no-chrome
prezo presentation.md -e png --slide 3
prezo presentation.md -e pdf --pdf-backend chrome
```

## Markdown Syntax

### Basic Structure

```markdown
---
title: My Presentation
author: Name
theme: dark
---

# First Slide

Content here...

---

# Second Slide

- Bullet points
- More content
```

### Layout Blocks

```markdown
::: columns              # Multi-column layout
::: column               # Column (inside columns)
::: column 40            # Column with width %
::: center               # Centered content
::: right                # Right-aligned content
::: box                  # Bordered panel
::: box "Title"          # Panel with title
::: spacer               # Vertical space (1 line)
::: spacer 3             # Vertical space (3 lines)
::: divider              # Horizontal line
::: divider double       # Double line (single/double/thick/dashed)
```

### Two-Column Example

```markdown
::: columns
::: column
Left content
:::
::: column
Right content
:::
:::
```

### Box Example

```markdown
::: box "Features"

**Title** - Description
- Item one
- Item two

:::
```

### Presenter Notes

```markdown
# Slide Title

Visible content

???

Notes after ??? separator
```

Or with HTML comment:

```markdown
<!-- notes: Your presenter notes here -->
```

### Images

```markdown
![](image.png)              # Inline image
![bg](image.png)            # Background
![bg left](image.png)       # Image left (50%), content right
![bg right](image.png)      # Image right (50%), content left
![bg right:40%](image.png)  # Image takes 40% width
![bg right:fit](image.png)  # Image fits vertically, width auto
![bg left:fit](image.png)   # Image fits vertically, width auto
![w:60](image.png)          # Width in characters
![h:20](image.png)          # Height in lines
```

### Prezo Directives

```markdown
<!-- prezo
theme: dracula
show_clock: true
show_elapsed: true
countdown_minutes: 45
time_budget: 30
incremental: true
image_mode: auto
-->
```

## Themes

`dark` | `light` | `dracula` | `solarized-dark` | `nord` | `gruvbox`

Press `T` to cycle during presentation.

## Configuration

Config file: `~/.config/prezo/config.toml`

```toml
[display]
theme = "dark"
show_clock = false
show_elapsed = true

[presentation]
countdown_minutes = 0
incremental = false

[images]
mode = "auto"
```

## Pacing Indicator

When `--time-budget` or `time_budget` is set:
- **▲ -Xm** (green) = ahead of schedule (>10%)
- **▼ +Xm** (red) = behind schedule (>10%)

## Tips

- One idea per slide
- 3-5 bullet points max
- Use `-I` for step-by-step reveals
- Press `o` to see all slides at once
- Use `::: box` to highlight key points
- Add presenter notes with `???`
- Use `--time-budget` to stay on track
