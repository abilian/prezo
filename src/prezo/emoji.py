r"""Emoji handling for terminal-safe rendering.

Terminal emulators disagree with Rich's `cell_len` on how many cells an emoji
occupies (especially VS16 sequences like ``⚠️`` and East-Asian-Wide glyphs like
``✅``). That mismatch clips emoji or breaks box/table borders. There is no
static width that is correct for every terminal + font, so the only guaranteed
fix is to avoid emitting ambiguous-width glyphs.

`replace_emoji` rewrites emoji to fixed-width ASCII markers (``[V]``, ``/!\``,
``[X]`` …) for the common, meaning-bearing ones, and strips the rest. The result
contains only width-1 characters, so alignment is identical on every terminal.
"""

from __future__ import annotations

import re

# Curated map of meaning-bearing emoji to fixed-width ASCII markers.
# Keys are the base code points; variation selectors are stripped beforehand so
# both ``✅`` and ``✅️`` (with U+FE0F) match the same entry.
EMOJI_MARKERS: dict[str, str] = {
    # Affirmative / done
    "✅": "[V]",  # ✅ white heavy check mark
    "✔": "[V]",  # ✔ heavy check mark
    "✓": "[V]",  # ✓ check mark
    "☑": "[V]",  # ☑ ballot box with check
    # Negative / removed
    "❌": "[X]",  # ❌ cross mark
    "❎": "[X]",  # ❎ negative squared cross mark
    "✖": "[X]",  # ✖ heavy multiplication x
    "✗": "[X]",  # ✗ ballot x
    "✘": "[X]",  # ✘ heavy ballot x
    "\U0001f6ab": "[X]",  # 🚫 no entry sign
    # Warning / attention
    "⚠": "/!\\",  # ⚠ warning sign
    "❗": "/!\\",  # ❗ heavy exclamation mark
    "❕": "/!\\",  # ❕ white exclamation mark
    "‼": "/!\\",  # ‼ double exclamation mark
    # Question
    "❓": "[?]",  # ❓ question mark
    "❔": "[?]",  # ❔ white question mark
    "⁉": "[?]",  # ⁉ exclamation question mark
    # Information / ideas
    "ℹ": "[i]",  # ℹ information source  # noqa: RUF001
    "\U0001f4a1": "[i]",  # 💡 light bulb
    # Emphasis / highlight
    "⭐": "[*]",  # ⭐ star
    "\U0001f31f": "[*]",  # 🌟 glowing star
    "✨": "[*]",  # ✨ sparkles
    "\U0001f525": "[*]",  # 🔥 fire
}

# Colour (terminal palette name) for each marker, used when rendering so the
# ASCII fallback keeps the visual cue the emoji carried. Palette names adapt to
# the active terminal/theme rather than being hard-coded RGB.
MARKER_STYLES: dict[str, str] = {
    "[V]": "green",
    "[X]": "red",
    "/!\\": "yellow",
    "[?]": "cyan",
    "[i]": "blue",
    "[*]": "magenta",
}

# Modifiers that should be dropped (they only tweak presentation, never width
# in a meaningful way once the base glyph is handled): variation selectors,
# skin-tone modifiers, zero-width joiner, and the keycap combining mark.
_MODIFIERS = re.compile(
    "["
    "︀-️"  # variation selectors (incl. VS16 emoji presentation)
    "\U0001f3fb-\U0001f3ff"  # skin-tone modifiers
    "‍"  # zero-width joiner
    "⃣"  # combining enclosing keycap
    "]"
)

# Broad emoji code-point ranges used to strip any emoji not in the curated map.
# Deliberately excludes the Arrows block (U+2190-U+21FF, e.g. ``→``), which are
# plain width-1 text characters that render reliably.
_EMOJI = re.compile(
    "["
    "☀-➿"  # Miscellaneous Symbols + Dingbats
    "\U0001f000-\U0001faff"  # all astral emoji blocks
    "]"
)


def replace_emoji(text: str) -> str:
    r"""Rewrite emoji to fixed-width ASCII so terminal alignment is preserved.

    Mapped emoji become short ASCII markers (``[V]``, ``/!\``, ``[X]`` …);
    any other emoji is stripped. Non-emoji symbols (arrows, box drawing, CJK)
    are left untouched.

    Args:
        text: Source text, possibly containing emoji.

    Returns:
        Text containing only reliably-width-1 characters in place of emoji.

    """
    if not text or not _has_emoji(text):
        return text

    # Drop presentation / skin-tone / ZWJ / keycap modifiers first so the base
    # glyph is matched cleanly by the curated map.
    text = _MODIFIERS.sub("", text)

    for emoji, marker in EMOJI_MARKERS.items():
        if emoji in text:
            text = text.replace(emoji, marker)

    # Strip any remaining (uncurated, decorative) emoji.
    text = _EMOJI.sub("", text)

    # Collapse runs of spaces left behind by stripped emoji (never newlines).
    return re.sub(r"[^\S\n]{2,}", " ", text)


def _has_emoji(text: str) -> bool:
    """Return True if the text contains any emoji or emoji modifier."""
    return bool(_EMOJI.search(text) or _MODIFIERS.search(text))
