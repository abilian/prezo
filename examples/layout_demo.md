---
title: Layout Features Demo
author: Prezo
---

# Layout Features

Demonstrating all layout directives

---

# Columns (existing)

::: columns
::: column
## Left Column

- Point one
- Point two
- Point three
:::
::: column
## Right Column

**Bold text** and *italic text*

Code: `inline code`
:::
:::

---

# Column Widths

::: columns
::: column 30
## 30%

Narrow sidebar
:::
::: column 70
## 70%

This column takes up most of the space.

It can contain longer paragraphs and more detailed content.
:::
:::

---

# Centered Content

::: center
## Centered Title

This text is horizontally centered.

**Perfect for quotes and emphasis**
:::

---

# Right-Aligned Content

::: right
— Attribution goes here

*Author Name, 2026*
:::

---

# Spacer Demo

Content above

::: spacer 2
:::

Content below (with 2 lines of space)

::: spacer
:::

Another gap (default 1 line)

---

# Box / Panel

::: box "Features"
- Feature one
- Feature two
- Feature three
:::

::: spacer
:::

::: box
A box without a title
:::

---

# Divider Styles

Single (default):

::: divider
:::

Double:

::: divider double
:::

Thick:

::: divider thick
:::

Dashed:

::: divider dashed
:::

---

# Combined Example

::: box "Quote"
"The best way to predict the future is to invent it."
:::

::: right
— Alan Kay
:::

::: divider double
:::

::: columns
::: column
## Pro
- Fast
- Simple
- Elegant
:::
::: column
## Con
- Learning curve
- Limited
:::
:::

---

# Complex Layout

::: center
## Product Comparison
:::

::: divider
:::

::: columns
::: column 33
::: box "Basic"
- 1 user
- 1GB storage
- Email support

**$9/month**
:::
:::


::: column 34
::: box "Pro"
- 5 users
- 10GB storage
- Priority support

**$29/month**
:::
:::

::: column 33
::: box "Enterprise"
- Unlimited
- Unlimited
- 24/7 support

**Contact us**
:::
:::
:::

---

# Thank You

::: center
Questions?
:::

::: spacer 2
:::

::: right
*github.com/example/prezo*
:::
