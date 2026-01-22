# Changelog

All notable changes to Prezo are documented in this file.

Starting with version 2026.1.1, Prezo uses [CalVer](https://calver.org/) versioning (YYYY.M.patch).

## [2026.1.2] - 2026-01-22

### Added
- **Column layouts** - Pandoc-style fenced div syntax for multi-column slides
  - `::: columns` / `::: column` for side-by-side content
  - Support for 2, 3, or more columns
  - Variable column widths (`::: column 30` for 30% width)
  - Works in TUI, PDF export, and HTML export
- **Centered content** - `::: center` for horizontally centered text
- **Right-aligned content** - `::: right` for right-aligned text (attributions, signatures)
- **Vertical spacing** - `::: spacer [n]` for adding blank lines (default 1)
- **Bordered panels** - `::: box [title]` for content in bordered boxes
- **Horizontal dividers** - `::: divider [style]` with styles: single, double, thick, dashed
- **Nested layout blocks** - Layout blocks can be nested inside columns
- New `SlideContent` widget with layout support
- New `layout.py` module for parsing and rendering layouts
- Demo presentations: `examples/columns_demo.md`, `examples/layout_demo.md`

### Changed
- Test suite reorganized into test pyramid structure (a_unit, b_integration, c_e2e)

### Fixed
- Emoji characters now render correctly in PDF export (added emoji font fallbacks)

## [2026.1.1] - 2026-01-06

### Changed
- Switched from SemVer to CalVer versioning

### Fixed
- Pillow deprecation warnings (`getdata()` replaced with `get_flattened_data()`)

### Documentation
- Updated tutorial with missing features (image_mode directive, bg fit/contain, w:/h: size syntax)
- Added CHANGES.md changelog

## [0.3.2] - 2025-12-16

### Fixed
- Type checker issues (mypy, pyrefly, ty)
- CI configuration

### Changed
- Tweaked default CSS for better slide layout

### Added
- Noxfile for development automation

## [0.3.1] - 2025-12-16

### Fixed
- Modal screens (help, overview, TOC, search) now use the current theme

## [0.3.0] - 2025-12-16

Initial public release.

### Features
- **Markdown presentations** - MARP/Deckset format with `---` slide separators
- **Live reload** - Auto-refresh when file changes (1s polling)
- **Keyboard navigation** - Vim-style keys, arrow keys, and more
- **Slide overview** - Grid view for quick navigation (`o`)
- **Search** - Find slides by content (`/`)
- **Table of contents** - Navigate by headings (`t`)
- **Go to slide** - Jump to specific slide number (`:`)
- **Presenter notes** - Toggle notes panel (`p`)
- **Themes** - 6 color schemes (`T` to cycle): dark, light, dracula, solarized-dark, nord, gruvbox
- **Timer/Clock** - Elapsed time and countdown (`c`)
- **Edit slides** - Open in $EDITOR (`e`), saves back to source file
- **Export** - PDF, HTML, PNG, SVG formats with customizable themes and sizes
- **Image support** - Inline and background images with MARP layout directives (left/right/fit)
- **Native image viewing** - Press `i` for full-quality image display (iTerm2/Kitty protocols)
- **Blackout/Whiteout** - Blank screen modes (`b`/`w`)
- **Command palette** - Quick access to all commands (`Ctrl+P`)
- **Config file** - Customizable settings via `~/.config/prezo/config.toml`
- **Recent files** - Tracks recently opened presentations
- **Position memory** - Remembers last slide position per file
