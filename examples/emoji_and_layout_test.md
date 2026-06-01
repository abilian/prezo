---
title: Emoji & Layout Test
theme: dark
---

# Emoji & Layout Test

This deck exercises the three recent fixes. Run it twice and compare:

- `prezo examples/emoji_and_layout_test.md`
- `prezo examples/emoji_and_layout_test.md --no-emoji`

With `--no-emoji`, every emoji below becomes a width-1 ASCII marker, so
alignment must be identical on **any** terminal.

---

# 1. Void directives — stray `:::`

These two blocks must render **identically** (no leaked `:::`).

**With a closing `:::` (old docs style):**

ABOVE
::: spacer 1
:::
BELOW

**Without a closing `:::` (void style):**

ABOVE
::: spacer 1
BELOW

If you see a literal `::: BELOW` anywhere above, the bug is back.

---

# 2. Divider — stray `:::`

Single, double, thick, dashed — none should leak a `:::`.

::: divider
::: divider double
:::
::: divider thick
::: divider dashed
:::

Text after the dividers should start cleanly, with no `:::` glued to it.

---

# 3. Box titles with emoji

The box border must stay aligned (screenshot-2 case).

::: box "Emerging model ⚠️ (proposal)"
- Class A ✅ — strategic, direct → strengthen upstream
- Class B ⚠️ — replaceable → keep optionality
- Class C ❌ — transitive tail → automate
:::

With `--no-emoji` the title reads `Emerging model /!\ (proposal)`.

---

# 4. Table with emoji

Column alignment must hold (screenshot-1 case).

| Capability        | Vulns | Incidents | Inform |
| ----------------- | :---: | :-------: | :----: |
| non-technical     |   —   |     —     |   —    |
| + IT infra        |   —   |     ✅    |   ✅   |
| + engineering     |   ✅  |     ✅    |   ✅   |
| + 1:1 users       |   ✅  |     ✅    |   ✅   |

With `--no-emoji` every ✅ becomes `[V]`.

---

# 5. Columns with nested boxes

Layout div containing boxes (the supported nesting direction).

::: columns
::: column
::: box "Pros ✅"
- Fast → ship
- Simple ⭐
:::
:::
::: column
::: box "Cons ⚠️"
- Learning curve
- Edge cases ❌
:::
:::
:::

---

# 6. Marker legend (for `--no-emoji`)

| Emoji | Marker |
| ----- | ------ |
| ✅ ✔️ ✓ | `[V]` |
| ❌ ✖️ 🚫 | `[X]` |
| ⚠️ ❗   | `/!\` |
| ❓ ⁉️   | `[?]` |
| 💡 ℹ️   | `[i]` |
| ⭐ ✨ 🔥 | `[*]` |

Arrows (→), box-drawing (│ ┌─┐) and CJK (中文) are **never** touched.
