"""Tests for terminal-safe emoji handling."""

from __future__ import annotations

from prezo.emoji import replace_emoji


class TestReplaceEmojiMarkers:
    """Meaning-bearing emoji become fixed-width ASCII markers."""

    def test_check_marks_become_v(self):
        assert replace_emoji("done ✅") == "done [V]"
        assert replace_emoji("done ✔️") == "done [V]"  # with VS16
        assert replace_emoji("done ✓") == "done [V]"

    def test_warning_becomes_bang(self):
        assert replace_emoji("⚠️ careful") == "/!\\ careful"
        assert replace_emoji("⚠ careful") == "/!\\ careful"  # without VS16

    def test_cross_becomes_x(self):
        assert replace_emoji("nope ❌") == "nope [X]"
        assert replace_emoji("nope ✖️") == "nope [X]"

    def test_markers_are_width_one_ascii(self):
        # Every character in the result must be a single-cell ASCII char.
        result = replace_emoji("✅ ⚠️ ❌")
        assert result == "[V] /!\\ [X]"
        assert all(ord(c) < 128 for c in result)


class TestReplaceEmojiStripsDecorative:
    """Uncurated/decorative emoji are stripped, leaving clean text."""

    def test_thumbs_up_with_skin_tone_removed(self):
        assert replace_emoji("nice 👍🏽 work") == "nice work"

    def test_unknown_emoji_removed(self):
        # 🎉 party popper has no curated marker.
        assert "🎉" not in replace_emoji("ship it 🎉")

    def test_no_double_spaces_left_behind(self):
        assert "  " not in replace_emoji("a 👍 b")


class TestReplaceEmojiPreservesText:
    """Non-emoji content (incl. ambiguous symbols) is left untouched."""

    def test_arrows_preserved(self):
        # → (U+2192) is a reliable width-1 character, not an emoji.
        assert replace_emoji("a → b") == "a → b"

    def test_box_drawing_preserved(self):
        assert replace_emoji("┌─┐ │ └─┘") == "┌─┐ │ └─┘"

    def test_cjk_preserved(self):
        assert replace_emoji("中文 テスト") == "中文 テスト"

    def test_plain_text_unchanged(self):
        assert replace_emoji("no emoji here") == "no emoji here"

    def test_empty_string(self):
        assert replace_emoji("") == ""

    def test_newlines_preserved(self):
        assert replace_emoji("line1\nline2") == "line1\nline2"
