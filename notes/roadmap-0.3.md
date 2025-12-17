# Prezo v0.3.0 - Polish & Developer Experience

**Status:** Complete ✓

## Overview

Focus on error handling, developer experience, and additional export formats.

## Completed Features

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

### Documentation Links
**Priority:** Low | **Effort:** Low

**Completed:**
- [x] Add documentation URL to help screen (GitHub, Issues)
- [x] Command palette mentioned in help and welcome

## Success Criteria

v0.3.0 is complete when:
1. ✓ Error messages are user-friendly and actionable
2. ✓ Command palette provides discoverability for all features
3. ✓ Individual slides can be exported as PNG/SVG images
