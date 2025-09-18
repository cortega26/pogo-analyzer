"""Verify packaging metadata exposes the expected CLI and optional extras."""

from __future__ import annotations

from pathlib import Path

import pytest

try:  # Python 3.11+
    import tomllib as toml_loader
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback.
    import tomli as toml_loader  # type: ignore[no-redef]


@pytest.fixture(scope="module")
def pyproject_data() -> dict[str, object]:
    """Return the parsed ``pyproject.toml`` dictionary for assertions."""

    path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with path.open("rb") as stream:
        return toml_loader.load(stream)


def test_console_script_entry(pyproject_data: dict[str, object]) -> None:
    """The project should publish the raid scoreboard CLI entry point."""

    project = pyproject_data["project"]
    assert isinstance(project, dict)
    scripts = project.get("scripts")
    assert isinstance(scripts, dict)
    assert scripts.get("pogo-raid-scoreboard") == "raid_scoreboard_generator:main"


def test_pandas_optional_dependency(pyproject_data: dict[str, object]) -> None:
    """Excel exports should be declared under the pandas optional dependency group."""

    project = pyproject_data["project"]
    assert isinstance(project, dict)
    optional = project.get("optional-dependencies")
    assert isinstance(optional, dict)
    pandas_deps = optional.get("pandas")
    assert isinstance(pandas_deps, list)
    assert {"pandas>=2.0", "openpyxl>=3.1"}.issubset(set(pandas_deps))
