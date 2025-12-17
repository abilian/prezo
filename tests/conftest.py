"""Shared pytest fixtures for Prezo tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_presentation_md() -> str:
    """Sample MARP-style presentation markdown."""
    return """---
title: Test Presentation
theme: default
---

# First Slide

Welcome to the presentation!

---

## Second Slide

- Bullet point 1
- Bullet point 2

---

### Third Slide

Some content here.

???
These are presenter notes.
"""


@pytest.fixture
def marp_presentation_md() -> str:
    """Sample presentation with MARP-specific directives."""
    return """---
marp: true
header: MARP Header Title
theme: gaia
---

<!-- _class: lead -->

# Title Slide

![bg right](image.png)

---

## Content Slide

<div class="columns">

- Left column
- More content

</div>

<!-- _header: Custom Header -->
"""


@pytest.fixture
def simple_presentation_md() -> str:
    """Minimal presentation without frontmatter."""
    return """# Only Slide

Just one slide with no metadata.
"""
