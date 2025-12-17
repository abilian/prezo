# prezo Future Roadmap

Features under consideration for future releases (v0.4.0+).

## Theming Enhancements

### Syntax Highlighting Themes
**Priority:** Low | **Complexity:** Low

Different color schemes for code blocks.

- Rich supports Pygments styles
- Options: `monokai`, `github-dark`, `one-dark`, `nord`, `solarized`, etc.
- Configure via frontmatter or config file

### CSS-like Styling (TCSS)
**Priority:** Medium | **Complexity:** High

Custom styling for presentations using Textual CSS.

- Per-presentation styles from frontmatter
- Custom TCSS file support: `prezo.tcss`
- Slide-specific classes via MARP-style directives
- Custom fonts and colors

## Content Features

### Better Table Rendering
**Priority:** Low | **Complexity:** Medium

Improved markdown table display.

- Auto-column width adjustment
- Box drawing characters for borders
- Header row styling
- Cell alignment support (left, center, right)

### Bookmarks
**Priority:** Low | **Complexity:** Medium

Mark slides for quick return during presentation.

- Press `m` to toggle bookmark on current slide
- Press `'` to open bookmarks list
- Visual indicator on bookmarked slides
- Persist bookmarks in state file

### Annotations
**Priority:** Low | **Complexity:** High

Draw/annotate on slides during presentation.

- Freeform drawing overlay
- Highlight regions
- Clear annotations
- Optional: save annotations

## Export Enhancements

### Reveal.js Export
**Priority:** Low | **Complexity:** Medium

Export to reveal.js for web presentations.

- Generate reveal.js HTML structure
- Include speaker notes
- Preserve themes
- Optional: self-contained single file

### PowerPoint/Keynote Export
**Priority:** Low | **Complexity:** High

Export to native presentation formats.

- PPTX generation via python-pptx
- Keynote via intermediate format
- Preserve basic formatting

## Advanced Features

### Presenter View
**Priority:** Medium | **Complexity:** High

Separate window showing notes and preview.

- Current slide with notes
- Next slide preview
- Timer and progress
- Requires multi-window support

### Remote Control
**Priority:** Low | **Complexity:** High

Control presentation from another device.

- WebSocket server for commands
- QR code for connection
- Mobile-friendly web interface
- Next/previous/goto commands

### Collaborative Mode
**Priority:** Low | **Complexity:** Very High

Real-time collaboration on presentations.

- CRDT-based sync
- Multiple cursors
- Conflict resolution
- Requires server component

## Technical Improvements

### Plugin System
**Priority:** Medium | **Complexity:** High

Extensibility via plugins.

- Custom renderers
- Custom key bindings
- Custom export formats
- Plugin discovery and loading

### Performance Optimization
**Priority:** Low | **Complexity:** Medium

Improve performance for large presentations.

- Lazy slide rendering
- Virtual scrolling in overview
- Optimized image caching
- Background loading

## Non-Goals

The following are explicitly out of scope:

- **Full MARP CSS compatibility** - We support MARP markdown syntax but not CSS
- **Slide transitions/animations** - Terminal limitations make this impractical
- **Cloud sync** - Use git or file sync tools instead
- **WYSIWYG editing** - We focus on markdown-based workflow

## Priority Summary

| Priority | Features |
|----------|----------|
| Medium | CSS-like Styling, Presenter View, Plugin System |
| Low | Syntax Themes, Tables, Bookmarks, Reveal.js Export, Remote Control |
| Very Low | Annotations, PowerPoint Export, Collaborative Mode |
