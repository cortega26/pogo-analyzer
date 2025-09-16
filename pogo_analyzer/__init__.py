"""Utilities shared across the raid scoreboard tooling."""

from __future__ import annotations

import re
from importlib import metadata as _metadata
from pathlib import Path

from .data.raid_entries import (
    DEFAULT_RAID_ENTRIES,
    IVSpread,
    PokemonRaidEntry,
    build_entry_rows,
)
from .raid_entries import RAID_ENTRIES, build_rows
from .scoring import calculate_iv_bonus, calculate_raid_score, iv_bonus, raid_score
from .scoreboard import (
    ExportResult,
    ScoreboardExportConfig,
    TableLike,
    add_priority_tier,
    build_dataframe,
    build_export_config,
    generate_scoreboard,
)
from .simple_table import Row, SimpleSeries, SimpleTable


def _read_local_version() -> str:
    """Return the project version from ``pyproject.toml`` when not installed."""

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if pyproject.is_file():
        match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), re.MULTILINE)
        if match:
            return match.group(1)
    return "0.0.0"


try:
    __version__ = _metadata.version("pogo-analyzer")
except _metadata.PackageNotFoundError:
    __version__ = _read_local_version()

__all__ = [\n    "DEFAULT_RAID_ENTRIES",\n    "IVSpread",\n    "PokemonRaidEntry",\n    "RAID_ENTRIES",\n    "Row",\n    "SimpleSeries",\n    "SimpleTable",\n    "build_entry_rows",\n    "build_rows",\n    "TableLike",\n    "ScoreboardExportConfig",\n    "ExportResult",\n    "add_priority_tier",\n    "build_dataframe",\n    "build_export_config",\n    "generate_scoreboard",\n    "calculate_iv_bonus",\n    "calculate_raid_score",\n    "iv_bonus",\n    "raid_score",\n    "__version__",\n]\n
