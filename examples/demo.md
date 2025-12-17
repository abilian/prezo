---
title: prezo Demo
theme: default
author: Demo Author
---

<!-- prezo
theme: dark
show_clock: true
show_elapsed: true
-->

# prezo

## A TUI Presentation Tool

Built with Python and Textual

---

# Features

- **Markdown-based** presentations
- **MARP/Deckset** compatible format
- **Keyboard navigation** for smooth presenting
- **Terminal-native** - works over SSH!
- **Theme support** - dark, light, and more
- **Export** - PDF and HTML output

---

# Code Examples

prezo supports syntax highlighting:

```python
def hello_world():
    print("Hello from prezo!")

if __name__ == "__main__":
    hello_world()
```

---

# Navigation

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

---

# Display Controls

| Key | Action |
|-----|--------|
| `p` | Toggle notes panel |
| `c` | Cycle clock modes |
| `T` | Cycle themes |
| `b` | Blackout screen |
| `w` | Whiteout screen |
| `?` | Help screen |
| `q` | Quit |

---

# Lists and Formatting

## Bullet Points
- First item
- Second item
  - Nested item
  - Another nested item
- Third item

## Numbered List
1. Step one
2. Step two
3. Step three

---

# Blockquotes

> "The best way to predict the future is to invent it."
>
> — Alan Kay

---

# Configuration

Create `~/.config/prezo/config.toml`:

```toml
[display]
theme = "dark"

[timer]
show_clock = true
show_elapsed = true
countdown_minutes = 45

[behavior]
auto_reload = true
```

---

# Presentation Directives

Add directives to your presentation:

```markdown
<!-- prezo
theme: dracula
show_clock: true
countdown_minutes: 30
-->
```

These override global config for this presentation.

???
This is a presenter note! Press `p` to toggle notes.

---

# Image Support

![Demo shapes](images/demo.png)

Images render using **chafa** (if installed) or
**colored half-block characters** for best quality.

Press `i` to view images in native quality (suspend mode).

---

# Image Layouts: Left

![bg left](images/stack.png)

MARP-style directives position images:

```markdown
![bg left](images/stack.png)
```

The image appears on the **left** (50% width by default).

---

# Image Layouts: Right

![bg right](images/concept-map.png)

Place images on the right side:

```markdown
![bg right](images/concept-map.png)
```

Text content flows on the **left**.

---

# Image Layouts: Custom Size

![bg left:35%](images/lifecycle.png)

Control the image width with percentages:

```markdown
![bg left:35%](images/lifecycle.png)
```

This gives more space to text content.

---

# Export Options

## PDF Export
```bash
prezo --export presentation.md
prezo --export presentation.md --theme light
```

## HTML Export
```bash
prezo --html presentation.md
prezo --html presentation.md --notes
```

---

# Thank You!

## Get Started

```bash
pip install prezo
prezo examples/demo.md
```

**Happy Presenting!**
