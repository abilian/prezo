"""Nox configuration for Prezo."""

from __future__ import annotations

import nox

PYTHON_VERSIONS = ["3.12", "3.13", "3.14"]
DEFAULT_PYTHON = "3.12"

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["check", "test"]


@nox.session(python=PYTHON_VERSIONS)
def test(session: nox.Session) -> None:
    """Run the test suite."""
    session.run("uv", "sync", "--active", external=True)
    session.run("pytest", "tests", *session.posargs)


@nox.session(python=DEFAULT_PYTHON)
def check(session: nox.Session) -> None:
    """Run all checks (lint, typecheck, tests)."""
    session.run("uv", "sync", "--active", external=True)

    # Lint
    session.run("ruff", "check", "src", "tests")
    session.run("ruff", "format", "--check", ".")

    # Type check
    session.run("mypy", "src")
    session.run("ty", "check", "src")
    session.run("pyrefly", "check", "src")

    # Tests
    session.run("pytest", "tests", *session.posargs)
