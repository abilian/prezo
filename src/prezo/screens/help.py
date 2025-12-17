"""Help screen for Prezo."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, BindingType
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Markdown, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

HELP_CONTENT = """\
# Prezo Help

## Navigation Keys

| Key | Action |
|-----|--------|
| **→** / **j** / **Space** | Next slide |
| **←** / **k** | Previous slide |
| **Home** / **g** | First slide |
| **End** / **G** | Last slide |
| **:** | Go to specific slide |
| **/** | Search slides |
| **o** | Slide overview grid |
| **t** | Table of contents |

## Display Options

| Key | Action |
|-----|--------|
| **p** | Toggle presenter notes |
| **c** | Cycle clock/timer modes |
| **T** | Cycle through themes |
| **b** | Blackout screen |
| **w** | Whiteout screen |

## Editing & Files

| Key | Action |
|-----|--------|
| **e** | Edit current slide in $EDITOR |
| **r** | Reload presentation |

## Other

| Key | Action |
|-----|--------|
| **Ctrl+P** | Command palette |
| **?** | Show this help |
| **q** | Quit |
| **Escape** | Close dialogs |

## Presentation Format

Prezo supports **MARP/Deckset** style Markdown:

- YAML frontmatter for metadata
- `---` to separate slides
- `???` or `<!-- notes: -->` for presenter notes

### Prezo Directives

Add configuration to your presentation:

```markdown
<!-- prezo
theme: dark
show_clock: true
countdown_minutes: 45
-->
```

### Supported Directives

- `theme`: dark, light, dracula, solarized-dark, nord, gruvbox
- `show_clock`: true/false
- `show_elapsed`: true/false
- `countdown_minutes`: number

## Documentation

- **GitHub**: https://github.com/anthropics/prezo
- **Issues**: https://github.com/anthropics/prezo/issues

---

*Press Escape or ? to close*
"""


class HelpScreen(ModalScreen[None]):
    """Modal screen showing help content."""

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 80%;
        max-width: 100;
        height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #help-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding: 0 0 1 0;
    }

    #help-content {
        width: 100%;
        height: 1fr;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close", "Close"),
        Binding("question_mark", "close", "Close"),
        Binding("q", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the help screen layout."""
        with VerticalScroll(id="help-container"):
            yield Static("Prezo Help", id="help-title")
            yield Markdown(HELP_CONTENT, id="help-content")

    def action_close(self) -> None:
        """Close the help screen."""
        self.dismiss(None)
