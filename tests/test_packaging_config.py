"""Keeps the four places that name a Python version from drifting apart."""

from __future__ import annotations

import tomllib
from pathlib import Path

PYPROJECT = tomllib.loads(
    (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"),
)

SUPPORTED_VERSIONS = ((3, 14),)


def minimum_supported_version() -> tuple[int, int]:
    requires_python = PYPROJECT["project"]["requires-python"]
    assert requires_python.startswith(">=")
    major, minor = requires_python.removeprefix(">=").split(".")
    return int(major), int(minor)


def test_requires_python_is_the_lowest_supported_version() -> None:
    assert minimum_supported_version() == SUPPORTED_VERSIONS[0]


def test_classifiers_list_every_supported_version() -> None:
    classifiers = PYPROJECT["project"]["classifiers"]
    expected = [
        f"Programming Language :: Python :: {major}.{minor}" for major, minor in SUPPORTED_VERSIONS
    ]
    assert [item for item in classifiers if item in expected] == expected


def test_ruff_targets_the_minimum_supported_version() -> None:
    major, minor = minimum_supported_version()
    assert PYPROJECT["tool"]["ruff"]["target-version"] == f"py{major}{minor}"


def test_mypy_targets_the_minimum_supported_version() -> None:
    major, minor = minimum_supported_version()
    assert PYPROJECT["tool"]["mypy"]["python_version"] == f"{major}.{minor}"
