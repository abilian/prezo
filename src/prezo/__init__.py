"""Prezo - TUI-based presentation tool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ANSI color codes for error messages
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _error(message: str) -> None:
    """Print an error message and exit."""
    sys.stderr.write(f"{RED}{BOLD}error:{RESET} {message}\n")
    sys.exit(1)


def _warn(message: str) -> None:
    """Print a warning message."""
    sys.stderr.write(f"{YELLOW}{BOLD}warning:{RESET} {message}\n")


def _validate_file(path: Path, must_exist: bool = True) -> Path:
    """Validate a file path and return the resolved path.

    Args:
        path: The path to validate.
        must_exist: Whether the file must exist.

    Returns:
        The resolved absolute path.

    """
    resolved = path.resolve()

    if must_exist and not resolved.exists():
        _error(
            f"file not found: {path}\n\n"
            "Make sure the file exists and the path is correct."
        )

    if must_exist and resolved.is_dir():
        _error(
            f"expected a file, got a directory: {path}\n\nProvide a path to a .md file."
        )

    if must_exist and resolved.suffix.lower() not in (".md", ".markdown"):
        _warn(
            f"file '{path.name}' does not have a .md extension "
            "- treating as markdown anyway"
        )

    return resolved


def main() -> None:
    """Entry point for Prezo."""
    parser = argparse.ArgumentParser(
        prog="prezo",
        description="TUI-based presentation tool for Markdown slides",
        epilog="For more information, visit: https://github.com/abilian/prezo",
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to the presentation file (.md)",
    )
    parser.add_argument(
        "--export",
        "-e",
        metavar="FORMAT",
        choices=["pdf", "html", "png", "svg"],
        help="Export presentation to format (pdf, html, png, svg)",
    )
    parser.add_argument(
        "--slide",
        metavar="NUM",
        type=int,
        help="Export only slide number NUM (1-indexed, for png/svg export)",
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="PATH",
        help="Output path for export (default: same name with new extension)",
    )
    parser.add_argument(
        "--theme",
        "-t",
        metavar="NAME",
        default="dark",
        help="Theme for export (dark, light, dracula, solarized-dark, nord, gruvbox)",
    )
    parser.add_argument(
        "--size",
        "-s",
        metavar="WxH",
        default="80x24",
        help="Screen size for export as WIDTHxHEIGHT (default: 80x24)",
    )
    parser.add_argument(
        "--no-chrome",
        action="store_true",
        help="Export without window decorations (for printing)",
    )
    parser.add_argument(
        "--scale",
        metavar="FACTOR",
        type=float,
        default=2.0,
        help="Scale factor for PNG export (default: 2.0 for higher resolution)",
    )
    parser.add_argument(
        "--no-watch",
        action="store_true",
        help="Disable file watching for auto-reload",
    )
    parser.add_argument(
        "--config",
        "-c",
        metavar="PATH",
        help="Path to custom config file (default: ~/.config/prezo/config.toml)",
    )
    parser.add_argument(
        "--image-mode",
        metavar="MODE",
        choices=["auto", "kitty", "sixel", "iterm", "ascii", "none"],
        help="Image rendering mode (auto, kitty, sixel, iterm, ascii, none)",
    )

    args = parser.parse_args()

    # Load config from custom path or default
    from .config import load_config  # noqa: PLC0415

    config_path = Path(args.config) if args.config else None
    if config_path and not config_path.exists():
        _error(f"config file not found: {config_path}")

    config = load_config(config_path)

    # Override image mode if specified
    if args.image_mode:
        config.images.mode = args.image_mode

    if args.export:
        if not args.file:
            _error(
                "--export requires a presentation file\n\n"
                "Usage: prezo -e pdf presentation.md"
            )

        # Validate source file
        source_path = _validate_file(Path(args.file))

        # Parse size
        try:
            width, height = map(int, args.size.lower().split("x"))
        except ValueError:
            _error(
                f"invalid size format: {args.size}\n\n"
                "Use WIDTHxHEIGHT format (e.g., 80x24, 100x30)"
            )

        if args.export == "html":
            from .export import run_html_export  # noqa: PLC0415

            sys.exit(
                run_html_export(
                    str(source_path),
                    args.output,
                    theme=args.theme,
                ),
            )
        elif args.export in ("png", "svg"):
            from .export import run_image_export  # noqa: PLC0415

            sys.exit(
                run_image_export(
                    str(source_path),
                    args.output,
                    output_format=args.export,
                    theme=args.theme,
                    width=width,
                    height=height,
                    chrome=not args.no_chrome,
                    slide_num=args.slide,
                    scale=args.scale,
                ),
            )
        else:
            from .export import run_export  # noqa: PLC0415

            sys.exit(
                run_export(
                    str(source_path),
                    args.output,
                    theme=args.theme,
                    width=width,
                    height=height,
                    chrome=not args.no_chrome,
                ),
            )
    else:
        from .app import run_app  # noqa: PLC0415

        # Validate file if provided
        file_path = None
        if args.file:
            file_path = _validate_file(Path(args.file))

        run_app(file_path, watch=not args.no_watch, config=config)
