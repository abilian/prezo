# Writing Presentations in Markdown

This tutorial explains how to create presentations using the Markdown format supported by Prezo. It covers the slide syntax, formatting options, presenter notes, images, and configuration directives.

## Basic Structure

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

## Frontmatter

You can add YAML frontmatter at the beginning of your presentation to set metadata:

```markdown
---
title: My Presentation
author: Your Name
date: 2025-01-15
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

## Markdown Formatting

All standard Markdown formatting works within slides:

### Headings

```markdown
# Heading 1
## Heading 2
### Heading 3
```

### Text Styling

```markdown
**Bold text**
*Italic text*
~~Strikethrough~~
`inline code`
```

### Lists

```markdown
- Unordered item
- Another item
  - Nested item

1. Ordered item
2. Second item
3. Third item
```

### Code Blocks

````markdown
```python
def hello():
    print("Hello, World!")
```
````

Code blocks support syntax highlighting for most languages.

### Tables

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
```

### Blockquotes

```markdown
> This is a quote
> spanning multiple lines
```

### Links

```markdown
[Link text](https://example.com)
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
