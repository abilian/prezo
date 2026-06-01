---
title: Prezo Changelog
theme: dracula
---

# Prezo

## A TUI Presentation Tool

Terminal-native slides from Markdown — built with Python and Textual.
Themes, columns, images, export, and more. All from your terminal.

::: spacer

## What's New?

A journey through every release, from today back to day one.

---

# 2026.5.1 — Emoji-Safe & Faithful

## May 2026

::: columns
::: column
::: box "Terminal-Safe Emoji"
- `--no-emoji` rewrites emoji to aligned ASCII markers
- `[V]`, `/!\`, `[X]` — coloured, never clipped
- No more broken box or table borders
:::
:::

::: column
::: box "HTML Export Fixed"
- Headings, lists, tables and `:::` divs now render
- Before: it dumped raw Markdown source
:::
:::
:::

::: spacer

::: columns
::: column
- Void `::: spacer` / `::: divider` no longer leak a stray `:::`
:::

::: column
- Pinned `textual-image < 0.13` — no more help panel on launch
:::
:::

::: center
*Plus: `markdown` is now a real dependency, and clearer layout docs.*
:::

---

# 2026.4.2 — More Polish

## April 2026

::: columns
::: column
::: box "Boxes Fully Formatted"
- `*italic*`, `` `code` ``, and `[links](url)` now render inside `::: box` blocks
- Before: only **bold** worked. Now: everything does.
:::
:::

::: column
::: box "Wrapped Styling"
- Bold and italic spans survive across wrapped lines in list items
- No more stray `**` leaking through mid-paragraph
:::
:::
:::

::: spacer

::: center
*Plus: one fewer blank line before every box, and a fuller cheat sheet.*
:::

---

# 2026.4.1 — The Polish Release

## April 2026

::: columns
::: column
::: box "Code Blocks Fixed"
- `# comments` inside fenced code blocks no longer hijack the slide as H1 headings
- Write real code, with real comments!
:::
:::

::: column
::: box "Titles Done Right"
- `**bold**`, `*italic*`, and `code` in headings now render properly
- No more raw markdown leaking through
:::
:::
:::

::: spacer

::: center
*Long URLs in lists no longer snap in half mid-click*
:::

---

# 2026.2.4 — Under the Hood

## February 2026

::: center
A maintenance release focused on **code quality** and **type safety**.
:::

::: spacer

::: columns
::: column
::: box "Changed"
- Refactored complex functions
- Fixed type hints across the board
:::
:::

::: column
::: box "Fixed"
- Textual API compatibility
- Async `action_quit` signature
:::
:::
:::

---

# 2026.2.3 — Click All The Things

## February 2026

::: box "Links are now first-class citizens"
- **Click** markdown links to open them in your browser
- **Tab** into link navigation mode
- **j/k** to hop between links, **Enter** to open
:::

::: spacer

::: columns
::: column
- Hanging indent for wrapped list items
- Self-closing `::: spacer` and `::: divider`
:::

::: column
- Fixed inline image positioning
- Fixed relative link path resolution
:::
:::

---

# 2026.2.2 — Remember Everything

## February 2026

::: columns
::: column 60
::: box "Session Resume"
`prezo --resume presentation.md`

Pick up exactly where you left off: slide position, timer state, and theme are all restored.
:::
:::

::: column 40
::: box "Also New"
- `![bg right:fit]` image sizing
- Custom themes in config
- Custom CSS loading
:::
:::
:::

::: spacer

::: center
*Plus fixes for heading styles, theme cycling, and list spacing.*
:::

---

# 2026.2.1 — Timing is Everything

## February 2026

::: columns
::: column
::: box "New Controls"
- `-v` / `--version` flag
- `S` to pause/resume the timer
- Color-coded **pacing indicator** — are you ahead or behind?
:::
:::

::: column
::: box "Fixes"
- Box layout spacing tightened
- `--no-chrome` export no longer blank
- Cleaner vertical spacing in exports
:::
:::
:::

---

# 2026.1.3 — Print-Ready

## January 2026

::: box "Chrome PDF Backend"
Best-quality PDF export, powered by headless Chrome/Chromium.

`prezo -e pdf --pdf-backend chrome presentation.md`
:::

::: spacer

- Auto-detection: **Chrome** > **Inkscape** > **CairoSVG**
- Export module refactored into clean package structure
- Demo presentation: `docs/slides.md`

---

# 2026.1.2 — Layouts Arrive

## January 2026

::: columns
::: column
::: box "Columns"
- 2, 3, or more columns
- Variable widths
- Nested blocks inside columns
:::
:::

::: column
::: box "New Blocks"
- `::: center` — centered text
- `::: right` — right-aligned
- `::: spacer` — vertical space
- `::: box` — bordered panels
- `::: divider` — horizontal rules
:::
:::
:::

::: spacer

::: center
*The slide you're reading uses these very features.*
:::

---

# 2026.1.1 — CalVer Begins

## January 2026

::: center
Switched from SemVer to **CalVer** (YYYY.M.patch).

Because life's too short for `0.x` forever.
:::

::: spacer

- Fixed Pillow deprecation warnings
- Updated tutorial with missing features

---

# 0.3.x — The Early Days

## December 2025

::: columns
::: column
::: box "0.3.2"
- Type checker fixes
- Tweaked default CSS
- Noxfile for automation
:::
:::

::: column
::: box "0.3.1"
- Modal screens now follow the current theme
:::
:::
:::

---

# 0.3.0 — Day One

## December 2025

::: center
**Initial public release**
:::

::: columns
::: column
- Markdown presentations
- Live reload
- Keyboard navigation
- Slide overview & search
- Table of contents
- Presenter notes
:::

::: column
- 6 color themes
- Timer and clock
- Edit in `$EDITOR`
- PDF, HTML, PNG, SVG export
- Image support (Kitty/iTerm2)
- Command palette
:::
:::

::: spacer

::: center
*And so it began.*
:::
