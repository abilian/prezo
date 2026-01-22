---
title: Column Layout Demo
theme: dark
---

# Column Layout Demo

Testing Pandoc-style fenced div columns in Prezo.

---

## Basic Two Columns

::: columns
::: column
### Left Column

- First item
- Second item
- Third item
:::

::: column
### Right Column

- Alpha
- Beta
- Gamma
:::
:::

---

## Column with Different Content

::: columns
::: column
**Features:**

- Fast rendering
- Live reload
- Multiple themes
- Keyboard navigation
:::

::: column
**Benefits:**

1. Terminal-based
2. No dependencies
3. Markdown source
4. Easy to share
:::
:::

---

## Three Columns

::: columns
::: column
### One

Content in the first column.
:::

::: column
### Two

Content in the second column.
:::

::: column
### Three

Content in the third column.
:::
:::

---

## Centered Content

::: center
# This is Centered

This paragraph is centered on the slide.
:::

---

## Mixed Layout

Some intro text before the columns.

::: columns
::: column
Left side content with a list:

- Item A
- Item B
:::

::: column
Right side content:

> A blockquote here
:::
:::

Some outro text after the columns.

---

## Column Widths

::: columns
::: column 30
### Narrow (30%)

This column is narrower.
:::

::: column 70
### Wide (70%)

This column takes up more space with additional content to demonstrate
how text wraps differently in columns of different widths.
:::
:::

---

# Thank You!

Column layouts working in Prezo!
