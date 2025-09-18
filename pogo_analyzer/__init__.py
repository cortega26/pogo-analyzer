"""Utilities shared across the raid scoreboard tooling."""

from __future__ import annotations

import re
from importlib import metadata as _metadata
from pathlib import Path

from .data.base_stats import (
    BaseStats,
    BaseStatsRepository,
    load_base_stats,
    load_default_base_stats,
)
from .data.raid_entries import (
    DEFAULT_RAID_ENTRIES,
    DEFAULT_RAID_ENTRY_METADATA,
    IVSpread,
    PokemonRaidEntry,
    build_entry_rows,
    load_raid_entries,
)
from .formulas import damage_per_hit, effective_stats, infer_level_from_cp
from .raid_entries import RAID_ENTRIES, build_rows
from .scoreboard import (
    ExportResult,
    ScoreboardExportConfig,
    TableLike,
    add_priority_tier,
    build_dataframe,
    build_export_config,
    generate_scoreboard,
)
from .scoring import calculate_iv_bonus, calculate_raid_score, iv_bonus, raid_score
from .pve import compute_pve_score
from .pvp import compute_pvp_score
from .ui_helpers import pve_verdict, pvp_verdict, pve_tier
from .simple_table import Row, SimpleSeries, SimpleTable


def _read_local_version() -> str:
    """Return the project version from ``pyproject.toml`` when not installed."""

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if pyproject.is_file():
        match = re.search(
            r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), re.MULTILINE
        )
        if match:
            return match.group(1)
    return "0.0.0"


try:
    __version__ = _metadata.version("pogo-analyzer")
except _metadata.PackageNotFoundError:
    __version__ = _read_local_version()

__all__ = [
    "DEFAULT_RAID_ENTRIES",
    "DEFAULT_RAID_ENTRY_METADATA",
    "IVSpread",
    "PokemonRaidEntry",
    "RAID_ENTRIES",
    "Row",
    "SimpleSeries",
    "SimpleTable",
    "build_entry_rows",
    "load_raid_entries",
    "BaseStats",
    "BaseStatsRepository",
    "load_base_stats",
    "load_default_base_stats",
    "build_rows",
    "TableLike",
    "ScoreboardExportConfig",
    "ExportResult",
    "add_priority_tier",
    "build_dataframe",
    "build_export_config",
    "generate_scoreboard",
    "calculate_iv_bonus",
    "calculate_raid_score",
    "iv_bonus",
    "raid_score",
    "infer_level_from_cp",
    "effective_stats",
    "damage_per_hit",
    "compute_pve_score",
    "compute_pvp_score",
    "pve_verdict",
    "pvp_verdict",
    "pve_tier",
    "__version__",
]
