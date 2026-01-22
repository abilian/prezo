# Prezo User Guide

This guide explains how to use Prezo, a terminal-based presentation tool for Markdown slides. It covers installation, creating presentations, keyboard navigation, export options, and configuration.

## Quick Start

```bash
# Install prezo
pip install prezo

# Run a presentation
prezo presentation.md

# Export to PDF
prezo presentation.md --export pdf
```

## Writing Presentations

### Basic Structure

A Prezo presentation is a standard Markdown file with slides separated by `---` (three dashes on a line by itself).

```markdown
# My First Slide

Welcome to my presentation!

---

# Second Slide

- Point one
- Point two
- Point three

---

# Third Slide

More content here...
```

### Frontmatter

Add YAML frontmatter at the beginning of your presentation to set metadata:

```markdown
---
title: My Presentation
author: Your Name
date: 2026-01-15
theme: dark
---

# First Slide

Content starts here...
```

Supported frontmatter fields:
- `title` - Presentation title (shown in header)
- `author` - Author name
- `date` - Presentation date
- `theme` - Default theme (dark, light, dracula, solarized-dark, nord, gruvbox)

### Markdown Formatting

All standard Markdown formatting works within slides:

#### Headings

```markdown
# Heading 1
## Heading 2
### Heading 3
```

#### Text Styling

```markdown
**Bold text**
*Italic text*
~~Strikethrough~~
`inline code`
```

#### Lists

```markdown
- Unordered item
- Another item
  - Nested item

1. Ordered item
2. Second item
3. Third item
```

#### Code Blocks

````markdown
```python
def hello():
    print("Hello, World!")
```
````

Code blocks support syntax highlighting for most languages.

#### Tables

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
```

#### Blockquotes

```markdown
> This is a quote
> spanning multiple lines
```

#### Links

```markdown
[Link text](https://example.com)
```

## Layout Blocks

Prezo supports Pandoc-style fenced divs for creating layouts.

### Two Columns

```markdown
::: columns
::: column
**Left Column**

- First point
- Second point
:::

::: column
**Right Column**

- Another point
- More content
:::
:::
```

### Three or More Columns

```markdown
::: columns
::: column
Column 1
:::
::: column
Column 2
:::
::: column
Column 3
:::
:::
```

### Custom Column Widths

Specify width as a percentage (values should sum to ~100):

```markdown
::: columns
::: column 30
Narrow column (30%)
:::

::: column 70
Wide column (70%)
:::
:::
```

### Centered Content

Use `::: center` to horizontally center content:

```markdown
::: center
**This text is centered**

A centered paragraph with important information.
:::
```

### Right-Aligned Content

Use `::: right` for right-aligned text (useful for attributions):

```markdown
::: right
— Author Name, 2026
:::
```

### Vertical Spacing

Use `::: spacer` to add vertical space between elements:

```markdown
Content above

::: spacer 2
:::

Content below (with 2 lines of space)
```

### Bordered Panels

Use `::: box` to wrap content in a bordered panel:

```markdown
::: box "Features"
- Feature one
- Feature two
- Feature three
:::
```

The title is optional - you can also use `::: box` without a title.

### Horizontal Dividers

Use `::: divider` to add horizontal rules between sections:

```markdown
::: divider
:::
```

Available styles: `single` (default), `double`, `thick`, `dashed`:

```markdown
::: divider double
:::
```

### Nested Layout Blocks

Layout blocks can be nested inside columns:

```markdown
::: columns
::: column
::: box "Pro"
- Fast
- Simple
:::
:::
::: column
::: box "Con"
- Learning curve
:::
:::
:::
```

## Presenter Notes

Add presenter notes that are only visible in the notes panel (press `p` to toggle). There are two syntax options:

### Using `???` separator

```markdown
# My Slide

Visible content here.

???

These are presenter notes.
They won't appear on the slide itself.
- Remember to mention X
- Demo the feature
```

### Using HTML comments

```markdown
# My Slide

Visible content here.

<!-- notes: These are presenter notes using the comment syntax. -->
```

## Images

### Basic Images

```markdown
![Alt text](images/photo.png)
```

### MARP-Style Background Images

Prezo supports MARP-style image directives for positioning:

```markdown
# Slide with Right Image

![bg right](images/diagram.png)

Content appears on the left side.
```

Available positions:
- `![bg left](image.png)` - Image on left, content on right
- `![bg right](image.png)` - Image on right, content on left
- `![bg](image.png)` - Background image
- `![bg fit](image.png)` - Fit image to container
- `![bg contain](image.png)` - Same as fit

### Size Control

Control the image size as a percentage:

```markdown
![bg right:40%](images/small.png)   # Image takes 40% width
![bg left:60%](images/large.png)    # Image takes 60% width
```

Or specify exact dimensions in characters:

```markdown
![w:60](images/diagram.png)         # Width of 60 characters
![h:20](images/logo.png)            # Height of 20 lines
![w:40 h:15](images/chart.png)      # Both width and height
```

### Image Paths

Images can use relative paths from the presentation file:

```markdown
![](images/photo.png)        # Relative path
![](./images/photo.png)      # Explicit relative path
```

## Prezo Directives

Add a special HTML comment block to configure presentation behavior:

```markdown
<!-- prezo
theme: dracula
show_clock: true
show_elapsed: true
countdown_minutes: 45
-->

# First Slide
...
```

### Available Directives

| Directive | Values | Description |
|-----------|--------|-------------|
| `theme` | dark, light, dracula, solarized-dark, nord, gruvbox | Color theme |
| `show_clock` | true/false | Show current time |
| `show_elapsed` | true/false | Show elapsed time |
| `countdown_minutes` | number | Countdown timer (0 = disabled) |
| `image_mode` | auto, kitty, sixel, iterm, ascii, none | Image rendering mode |

## Keyboard Shortcuts

### Navigation

| Key | Action |
|-----|--------|
| `Right`, `Space`, `j` | Next slide |
| `Left`, `k` | Previous slide |
| `Home`, `g` | First slide |
| `End`, `G` | Last slide |
| `:` | Go to slide number |
| `/` | Search slides |

### Display

| Key | Action |
|-----|--------|
| `o` | Open slide overview grid |
| `t` | Show table of contents |
| `p` | Toggle presenter notes |
| `c` | Toggle clock display |
| `T` | Cycle through themes |
| `b` | Blackout screen |
| `w` | Whiteout screen |
| `i` | View current image |

### Other

| Key | Action |
|-----|--------|
| `e` | Edit current slide in $EDITOR |
| `r` | Reload presentation |
| `Ctrl+P` | Open command palette |
| `?` | Show help |
| `q` | Quit |

## Command Line Usage

### Basic Usage

```bash
# Run a presentation
prezo presentation.md

# Start with a specific theme
prezo presentation.md --theme dracula

# Disable auto-reload on file changes
prezo presentation.md --no-watch

# Use a specific image rendering mode
prezo presentation.md --image-mode kitty
```

### Exporting Presentations

Export to various formats for sharing or printing:

```bash
# Export to PDF
prezo presentation.md --export pdf

# Export to HTML
prezo presentation.md --export html

# Export all slides to PNG images
prezo presentation.md --export png

# Export all slides to SVG
prezo presentation.md --export svg

# Export a specific slide
prezo presentation.md --export png --slide 3

# Specify output path
prezo presentation.md --export pdf --output slides.pdf
```

### PDF Export Options

```bash
# Use Chrome for best quality (default if available)
prezo presentation.md --export pdf --pdf-backend chrome

# Use Inkscape
prezo presentation.md --export pdf --pdf-backend inkscape

# Use CairoSVG (fallback, may have alignment issues)
prezo presentation.md --export pdf --pdf-backend cairosvg

# Export without window decorations (for printing)
prezo presentation.md --export pdf --no-chrome
```

### Image Export Options

```bash
# Higher resolution PNG (scale factor)
prezo presentation.md --export png --scale 3.0

# Custom size
prezo presentation.md --export png --size 120x40

# Export with light theme
prezo presentation.md --export png --theme light
```

## Configuration

### Configuration File

Prezo reads configuration from `~/.config/prezo/config.toml`:

```toml
[display]
theme = "dark"
show_clock = false
show_elapsed = true

[presentation]
countdown_minutes = 0

[images]
mode = "auto"  # auto, kitty, sixel, iterm, ascii, none

[export]
default_theme = "dark"
default_size = "80x24"
```

### Per-Presentation Configuration

Use frontmatter or `<!-- prezo -->` directives to override global settings for specific presentations.

## Complete Example

Here's a complete presentation example:

```markdown
---
title: Introduction to Python
author: Jane Developer
---

<!-- prezo
theme: nord
show_elapsed: true
countdown_minutes: 30
-->

# Introduction to Python

A beginner-friendly programming language

---

# Why Python?

![bg right:40%](images/python-logo.png)

- Easy to learn
- Readable syntax
- Large ecosystem
- Versatile applications

???

Mention that Python is used by:
- Google, Netflix, Instagram
- Data scientists and researchers
- Web developers

---

# Hello World

```python
print("Hello, World!")
```

Simple and intuitive!

---

# Data Types

| Type | Example | Description |
|------|---------|-------------|
| `int` | `42` | Integer numbers |
| `float` | `3.14` | Decimal numbers |
| `str` | `"hello"` | Text strings |
| `list` | `[1, 2, 3]` | Ordered collections |

---

# Questions?

> The best way to learn is by doing.

Thank you for attending!

<!-- notes: Open the floor for Q&A. Have backup slides ready. -->
```

## Tips for Effective Presentations

1. **Keep slides focused** - One main idea per slide
2. **Use headings** - Start each slide with a clear heading
3. **Limit bullet points** - 3-5 points maximum per slide
4. **Use code sparingly** - Show only relevant snippets
5. **Add presenter notes** - Include talking points you might forget
6. **Test your images** - Verify paths and positioning before presenting
7. **Practice navigation** - Learn the keyboard shortcuts

## File Organization

A recommended project structure:

```
my-presentation/
├── presentation.md
└── images/
    ├── diagram.png
    ├── photo.jpg
    └── logo.svg
```

## Compatibility

Prezo's format is compatible with:
- **MARP** - Most directives work identically
- **Deckset** - Basic slide separation and notes syntax
- **Standard Markdown** - Files render correctly in any Markdown viewer

This means you can view your presentations in other tools or convert them to different formats while still benefiting from Prezo's terminal-based presentation mode.

## Troubleshooting

### Images not displaying

- Verify image paths are relative to the presentation file
- Check that your terminal supports the image protocol (Kitty, iTerm2, or Sixel)
- Try `--image-mode ascii` for basic terminals

### PDF export issues

- Install Chrome or Chromium for best results: `brew install --cask google-chrome`
- Alternatively, install Inkscape: `brew install inkscape`
- Ensure fonts are installed (Fira Code recommended)

### Alignment problems in exports

- Use `--pdf-backend chrome` for best text alignment
- CairoSVG has known issues with text positioning
