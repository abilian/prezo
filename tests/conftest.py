"""Shared pytest fixtures and configuration for Prezo tests.

Test Pyramid Structure:
- tests/a_unit/       - Unit tests (fast, isolated, no I/O)
- tests/b_integration/ - Integration tests (component interactions, file I/O)
- tests/c_e2e/        - End-to-end tests (full app/CLI workflows)

Run specific test types:
    uv run pytest -m unit              # Run only unit tests
    uv run pytest -m integration       # Run only integration tests
    uv run pytest -m e2e               # Run only e2e tests
    uv run pytest tests/a_unit/        # Run by directory
"""

from __future__ import annotations

from pathlib import Path

import pytest


def pytest_collection_modifyitems(config, items):
    """Automatically apply markers based on test directory."""
    assert config
    for item in items:
        # Get the path relative to tests/
        test_path = Path(item.fspath)
        parts = test_path.parts

        # Apply markers based on directory
        if "a_unit" in parts:
            item.add_marker(pytest.mark.unit)
        elif "b_integration" in parts:
            item.add_marker(pytest.mark.integration)
        elif "c_e2e" in parts:
            item.add_marker(pytest.mark.e2e)


# -----------------------------------------------------------------------------
# Shared Fixtures
# -----------------------------------------------------------------------------


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
