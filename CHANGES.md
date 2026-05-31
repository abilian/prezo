# Changelog

All notable changes to Prezo are documented in this file.

Starting with version 2026.1.1, Prezo uses [CalVer](https://calver.org/) versioning (YYYY.M.patch).

## [2026.5.1] - 2026-05-31

### Added
- **`--no-emoji` flag / `[display] emoji` option** - Rewrites emoji to fixed-width ASCII markers (`✅`→`[V]`, `⚠️`→`[!]`, `❌`→`[X]`, `❓`→`[?]`, …; decorative emoji are stripped). Terminals disagree with Rich on emoji cell width — some clip wide glyphs, others miscount VS16 sequences like `⚠️` and break box/table borders. Since no static width is correct for every terminal+font, this guarantees alignment by emitting only width-1 characters. Applies to the TUI and to HTML/PNG/SVG/PDF export (keeping exports a faithful image of the console). Arrows, box-drawing, and CJK text are left untouched.

### Fixed
- **Stray `:::` after `spacer`/`divider`** - `::: spacer` and `::: divider` are void directives that take no body. A redundant closing `:::` (which the docs used to show, and which appears in many decks) is now consumed instead of leaking as literal text glued to the following line.
- **HTML export rendered raw Markdown** - `--export html` now renders headings, lists, tables, code, and Pandoc-style fenced divs (`::: columns`, `::: box`, `::: center`, `::: right`, `::: divider`, `::: spacer`) into proper HTML elements. Previously the output dumped unrendered source (e.g. `<p># Title</p>`, `<p>::: columns</p>`) because the `markdown` library was never a runtime dependency and fenced divs were never routed through a renderer.

### Changed
- **`markdown` is now a runtime dependency** - required for faithful HTML export (it was previously only referenced optionally and never installed).

### Documentation
- **Void directives** - Tutorial now shows `::: spacer` / `::: divider` without a closing `:::` and notes the trailing marker is optional.
- **Box nesting** - Documented that `::: box` bodies are plain Markdown: a layout div may contain a box, but a box cannot contain nested fenced divs.

## [2026.4.2] - 2026-04-23

### Fixed
- **Inline formatting in boxes** - `*italic*`, `` `code` ``, and `[links](url)` inside `::: box` blocks now render properly (previously only `**bold**` worked)
- **Wrapped bold/italic** - Bold and italic spans in list items no longer lose their styling when word-wrapping splits them across lines
- **Extra space before boxes** - Removed the duplicated blank line that appeared before every box block (Rich's Markdown renderer already contributes the needed spacing)

### Documentation
- **Cheat sheet** - Documented link navigation mode (`Tab`, `j`/`k`, `Enter`, `Escape`) and the `-v` version flag

## [2026.4.1] - 2026-04-08

### Fixed
- **Code blocks** - `#` comments inside fenced code blocks are no longer rendered as H1 headings
- **Bold in titles** - `**bold**`, `*italic*`, `` `code` `` and links in H1/H2 headings now render with proper styling instead of showing raw markers
- **URL splitting in lists** - Markdown links and bare URLs in list items are no longer broken across lines during word wrapping

## [2026.2.4] - 2026-02-27

### Changed
- **Code quality improvements** - Refactored complex functions
- **Type annotations** - Fixed type hints for compatibility with mypy, pyrefly & ty

### Fixed
- **Textual API compatibility** - Updated `stylesheet.add_source()` call to use correct parameter names
- **Async action_quit** - Fixed method signature to match Textual's async parent class

## [2026.2.3] - 2026-02-06

### Added
- **Clickable links** - Click on markdown links to open them (URLs open in browser, local files in default app)
- **Link navigation mode** - Press `Tab` to enter link mode, `j`/`k` to navigate between links, `Enter` to open, `Escape` to exit
- **Hanging indent for lists** - Continuation lines of bullet points now align with text after the bullet, not with the bullet itself

### Changed
- **Self-closing spacers/dividers** - `::: spacer` and `::: divider` no longer require a closing `:::` tag

### Fixed
- **Inline images** - Images without `bg` directive now display properly below the title (centered, taking available space)
- **Link path resolution** - Relative paths in links resolve relative to the presentation file (consistent with image paths)

## [2026.2.2] - 2026-02-05

### Added
- **Session resume** - New `--resume` / `-r` flag to restore session state (slide position, timer elapsed time, timer running state, theme) when relaunching a presentation
- **Image vertical fit** - New `![bg right:fit]` and `![bg left:fit]` syntax to size images to fill vertical space while maintaining aspect ratio
- **Custom themes** - Define custom color themes in `~/.config/prezo/config.toml` using `[themes.name]` sections
- **Custom CSS** - Load custom Textual CSS from `~/.config/prezo/custom.tcss`, config-specified path, or local `./prezo.tcss`

### Fixed
- **Heading styles** - H1 (heavy border panel) and H2 (centered bold) now render consistently across all slides
- **Theme cycling** - Backgrounds now update correctly when cycling through themes with `T`
- **Bullet list spacing** - One blank line before and after each bullet list block (was inconsistent)
- **Numbered list spacing** - Empty lines between list items in source no longer create extra spacing

### Documentation
- Updated cheat-sheet and tutorial with `--resume` and `right:fit`/`left:fit` syntax

## [2026.2.1] - 2026-02-03

### Added
- **Version flag** - New `-v/--version` CLI option to display version
- **Timer start/stop** - New `S` key to pause/resume the elapsed timer (shows ⏸ indicator when paused)
- **Pacing indicator** - Color-coded indicator showing if you're ahead/behind schedule when a time budget is set (`--time-budget` flag or `time_budget` directive)

### Fixed
- **Box layout spacing** - Stacked boxes now have exactly one blank line between them (was two)
- **Box content spacing** - Title followed by list no longer has extra blank line in boxes
- **`--no-chrome` export** - Fixed blank page output when exporting without window decorations
- **Export vertical spacing** - Removed wasted blank lines at bottom of PDF/PNG/SVG exports
- Custom box content renderer for compact spacing (avoids Rich Markdown's paragraph gaps)

## [2026.1.3] - 2026-01-22

### Added
- **Chrome PDF backend** - Best quality PDF export using Chrome/Chromium headless
- **PDF backend selection** - New `--pdf-backend` CLI option (auto, chrome, inkscape, cairosvg)
- Demo presentation showcasing Prezo features (`docs/slides.md`)

### Changed
- PDF backend auto-detection now prefers Chrome > Inkscape > CairoSVG
- Export functions now return `Path` and raise `ExportError` instead of returning `(int, str)` tuples
- Export module refactored into a package (`export/`) with separate modules for PDF, HTML, images, and SVG
- Tutorial expanded into comprehensive user guide with CLI usage, keyboard shortcuts, configuration, and troubleshooting

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
