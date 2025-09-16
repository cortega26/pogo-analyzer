"""Reusable helpers for building and exporting the raid scoreboard."""

from __future__ import annotations

from argparse import Namespace
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, TypeAlias

from pogo_analyzer.data import DEFAULT_RAID_ENTRIES, PokemonRaidEntry, build_entry_rows
from pogo_analyzer.scoring import (
    calculate_iv_bonus,
    calculate_raid_score,
    iv_bonus,
    raid_score,
)
from pogo_analyzer.tables import Row, SimpleTable

pd: ModuleType | None
try:  # Prefer pandas for richer tabular output when available.
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - executed when pandas is absent.
    pd = None

if TYPE_CHECKING:  # pragma: no cover - type checking only.
    from pandas import DataFrame as PandasDataFrame
else:  # pragma: no cover - runtime fallback for type checking hints.
    PandasDataFrame = Any

TableLike: TypeAlias = SimpleTable | PandasDataFrame

RAID_ENTRIES = DEFAULT_RAID_ENTRIES
build_rows = build_entry_rows

# Backwards compatibility aliases for historical naming.
score = raid_score


@dataclass(frozen=True)
class ScoreboardExportConfig:
    """Configuration describing how scoreboard exports should be produced."""

    csv_path: Path
    excel_path: Path | None
    preview_limit: int = 10

    def __post_init__(self) -> None:
        if self.preview_limit <= 0:
            raise ValueError("preview_limit must be a positive integer.")

    @property
    def excel_requested(self) -> bool:
        """Return ``True`` when an Excel file should be attempted."""

        return self.excel_path is not None


@dataclass(frozen=True)
class ExportResult:
    """Outcome of :func:`generate_scoreboard`."""

    table: TableLike
    csv_path: Path
    excel_path: Path | None
    excel_written: bool
    excel_error: str | None


def _truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_output_path(base_dir: Path, value: str | Path) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()


def build_export_config(
    args: Namespace,
    env: Mapping[str, str] | None = None,
) -> ScoreboardExportConfig:
    """Construct export settings by merging CLI arguments and environment variables."""

    env = env or os.environ
    if args.output_dir is not None:
        base_dir = Path(args.output_dir).expanduser()
    else:
        env_dir = env.get("RAID_SCOREBOARD_OUTPUT_DIR")
        base_dir = Path(env_dir).expanduser() if env_dir else Path.cwd()

    csv_name = args.csv_name or env.get("RAID_SCOREBOARD_CSV") or "raid_scoreboard.csv"
    csv_path = _resolve_output_path(base_dir, csv_name)

    disable_excel = args.no_excel or _truthy(env.get("RAID_SCOREBOARD_DISABLE_EXCEL"))
    if disable_excel:
        excel_path = None
    else:
        excel_name = (
            args.excel_name
            or env.get("RAID_SCOREBOARD_EXCEL")
            or "raid_scoreboard.xlsx"
        )
        excel_path = _resolve_output_path(base_dir, excel_name)

    preview_limit = args.preview_limit
    if preview_limit is None:
        preview_env = env.get("RAID_SCOREBOARD_PREVIEW_LIMIT")
        if preview_env is not None:
            try:
                preview_limit = int(preview_env)
            except ValueError as exc:  # pragma: no cover - defensive guard.
                raise ValueError(
                    "RAID_SCOREBOARD_PREVIEW_LIMIT must be an integer."
                ) from exc
    if preview_limit is None:
        preview_limit = 10
    if preview_limit <= 0:
        raise ValueError("preview_limit must be a positive integer.")

    return ScoreboardExportConfig(
        csv_path=csv_path, excel_path=excel_path, preview_limit=preview_limit
    )


def _as_table(rows: Sequence[Row]) -> TableLike:
    """Return a pandas DataFrame or :class:`SimpleTable` depending on availability."""

    if pd is not None:
        return pd.DataFrame(rows)
    return SimpleTable(rows)


def build_dataframe(
    entries: Sequence[PokemonRaidEntry] = RAID_ENTRIES,
) -> TableLike:
    """Construct a tabular object from raid entries."""

    rows = build_entry_rows(entries)
    return _as_table(rows)


def add_priority_tier(df: TableLike) -> TableLike:
    """Append a human-readable priority tier based on ``Raid Score (1-100)``."""

    def tier(x: float) -> str:
        if x >= 90:
            return "S (Build ASAP)"
        if x >= 85:
            return "A (High)"
        if x >= 78:
            return "B (Good)"
        if x >= 70:
            return "C (Situational)"
        return "D (Doesn't belong on a Raids list)"

    df["Priority Tier"] = df["Raid Score (1-100)"].apply(tier)
    return df


def generate_scoreboard(
    entries: Sequence[PokemonRaidEntry] = RAID_ENTRIES,
    *,
    config: ScoreboardExportConfig,
) -> ExportResult:
    """Build, rank, and persist the raid scoreboard."""

    table = build_dataframe(entries)
    table = table.sort_values(by="Raid Score (1-100)", ascending=False).reset_index(drop=True)
    table = add_priority_tier(table)

    config.csv_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(config.csv_path, index=False)

    excel_path = config.excel_path
    excel_written = False
    excel_error: str | None = None
    if excel_path is None:
        excel_error = "disabled"
    elif isinstance(table, SimpleTable) or pd is None:
        excel_error = "pandas-missing"
    else:
        try:
            excel_path.parent.mkdir(parents=True, exist_ok=True)
            table.to_excel(excel_path, index=False)
            excel_written = True
        except Exception as exc:  # pragma: no cover - depends on optional engines.
            excel_error = str(exc)

    return ExportResult(
        table=table,
        csv_path=config.csv_path,
        excel_path=excel_path,
        excel_written=excel_written,
        excel_error=excel_error,
    )


__all__ = [
    "TableLike",
    "RAID_ENTRIES",
    "Row",
    "SimpleTable",
    "ScoreboardExportConfig",
    "ExportResult",
    "build_entry_rows",
    "build_rows",
    "build_dataframe",
    "build_export_config",
    "add_priority_tier",
    "generate_scoreboard",
    "calculate_iv_bonus",
    "calculate_raid_score",
    "iv_bonus",
    "raid_score",
    "score",
]
