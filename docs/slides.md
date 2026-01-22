---
title: Prezo - Terminal Presentations
author: Prezo Team
---
# Prezo

## Terminal-Native Presentations

::: center
**Present like a hacker. Write in Markdown.**
:::

::: spacer 2
:::

::: columns
::: column
- No browser needed
- No Electron bloat
- Pure terminal goodness
:::
::: column
- Vim-style navigation
- Live file watching
- Instant reload
:::
:::

::: center
*Get it with `pip install prezo`*
:::

???

Welcome to Prezo! This is a demo presentation showcasing the key features.
Press 'p' to toggle these presenter notes.

---
# Beautiful Layouts

::: columns
::: column
::: box "Left Panel"
- Multi-column layouts
- Bordered panels with titles
- Horizontal dividers
- Vertical spacers
:::
:::

::: column
::: box "Right Panel"
- Centered text blocks
- Right-aligned content
- Nested layouts
- Custom column widths
:::
:::
:::

::: divider double
:::

::: center
**Pandoc-style fenced divs** make complex layouts simple
:::

::: spacer 1
:::

::: right
— No CSS required
:::

---
# Code That Shines

Syntax highlighting for 100+ languages:

::: columns
::: column
**Python**
```python
def fib(n: int) -> int:
    """Calculate nth Fibonacci."""
    match n:
        case 0 | 1:
            return n
        case _:
            return fib(n-1) + fib(n-2)
```
:::

::: column
**Rust**
```rust
fn fib(n: u64) -> u64 {
    match n {
        0 | 1 => n,
        _ => fib(n-1) + fib(n-2),
    }
}
```
:::
:::

::: spacer 1
:::

::: center
**Rich** renders your code with full syntax highlighting
:::

---
# Six Stunning Themes

::: columns
::: column
::: box "Dark Themes"
- **dark** - Classic terminal
- **dracula** - Purple elegance
- **nord** - Arctic frost
- **gruvbox** - Retro warmth
:::
:::

::: column
::: box "Light Themes"
- **light** - Clean & bright
- **solarized-dark** - Easy on eyes
:::

::: spacer 1
:::

Press `T` to cycle themes live!
:::
:::

::: divider dashed
:::

::: center
Themes apply to TUI display **and** all exports
:::

---
# Export Anywhere

| Format | Command | Use Case |
|--------|---------|----------|
| **PDF** | `--export pdf` | Sharing, printing |
| **HTML** | `--export html` | Web publishing |
| **PNG** | `--export png` | Social media |
| **SVG** | `--export svg` | Vector graphics |

::: spacer 1
:::

::: columns
::: column
::: box "PDF Backends"
- Chrome (best quality)
- Inkscape
- CairoSVG
:::
:::

::: column
```bash
prezo slides.md \
  --export pdf \
  --pdf-backend chrome \
  --theme nord
```
:::
:::

---
# Keyboard Mastery

::: columns
::: column 33
::: box "Navigate"
| Key | Action |
|-----|--------|
| `j/k` | Next/Prev |
| `g/G` | First/Last |
| `/` | Search |
| `:` | Go to # |
:::
:::

::: column 33
::: box "Display"
| Key | Action |
|-----|--------|
| `o` | Overview |
| `t` | TOC |
| `p` | Notes |
| `T` | Theme |
:::
:::

::: column 34
::: box "Actions"
| Key | Action |
|-----|--------|
| `e` | Edit |
| `r` | Reload |
| `b/w` | Black/White |
| `?` | Help |
:::
:::
:::

::: divider thick
:::

::: center
**`Ctrl+P`** opens the command palette
:::

???

Try pressing these keys now!
- 'o' for slide overview grid
- 't' for table of contents
- '?' for full help screen
