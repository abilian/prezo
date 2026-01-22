# Prezo v0.3.0 - Polish & Developer Experience

**Status:** Complete ✓

## Overview

Focus on error handling, developer experience, additional export formats, and native image support.

## Completed Features

### Native Image Viewing
**Priority:** Medium | **Effort:** Medium

Full-quality image viewing using terminal graphics protocols.

**Completed:**
- [x] Press `i` to view images at native quality
- [x] Support for iTerm2 inline images protocol
- [x] Support for Kitty graphics protocol
- [x] textual-image integration for image display
- [x] Automatic protocol detection

### Better Error Handling
**Priority:** Medium | **Effort:** Low

Improved error messages and recovery.

**Completed:**
- [x] Friendly errors for missing files (colored ANSI output)
- [x] File validation with helpful messages
- [x] Non-.md file warnings
- [ ] Parse error recovery (show partial content) - deferred
- [ ] Graceful handling of malformed markdown - deferred

### Command Palette
**Priority:** Medium | **Effort:** Medium

Textual command palette integration for discoverability.

**Completed:**
- [x] Press `Ctrl+P` for command palette
- [x] Register all actions as commands (navigation, view, theme, screen, file)
- [x] Fuzzy search commands
- [x] Show keyboard shortcuts in command descriptions

### PNG/SVG Export
**Priority:** Low | **Effort:** Low

Export individual slides as images.

**Completed:**
- [x] Add `--export png` option
- [x] Add `--export svg` option
- [x] Export single slide: `--slide 3`
- [x] Export all slides to directory
- [x] Naming convention: `slide_001.png`, `slide_002.png`, etc.

**Usage:**
```bash
prezo -e png presentation.md              # All slides
prezo -e svg presentation.md --slide 3    # Single slide
prezo -e png presentation.md -o ./slides/ # Output directory
```

### Documentation
**Priority:** Low | **Effort:** Low

**Completed:**
- [x] Add documentation URL to help screen (GitHub, Issues)
- [x] Command palette mentioned in help and welcome
- [x] Tutorial: "Writing Presentations in Markdown" (`docs/tutorial.md`)

### Bug Fixes (v0.3.1, v0.3.2)

- [x] Modal screens now use the current theme
- [x] Help modal scrollbar fix
- [x] Type checker fixes (mypy, pyrefly, ty)
- [x] Pillow deprecation warnings fixed (`getdata()` → `get_flattened_data()`)
- [x] Slide layout adjusted for more content space

## Success Criteria

v0.3.0 is complete when:
1. ✓ Error messages are user-friendly and actionable
2. ✓ Command palette provides discoverability for all features
3. ✓ Individual slides can be exported as PNG/SVG images
4. ✓ Native image viewing works in supported terminals

---

## Post-0.3 Releases (CalVer: 2026.x.x)

Starting with 2026.1.1, Prezo switched to CalVer versioning.

### 2026.1.2

**Column Layouts**
- [x] Pandoc-style fenced div syntax (`::: columns`, `::: column`)
- [x] Support for 2, 3, or more columns
- [x] Variable column widths (`::: column 30` for 30%)
- [x] Centered content (`::: center`)
- [x] Layout support in TUI, PDF, and HTML export
- [x] New `layout.py` module and `SlideContent` widget

**Other**
- [x] Test pyramid reorganization (a_unit, b_integration, c_e2e)
- [x] Emoji font support in PDF export
