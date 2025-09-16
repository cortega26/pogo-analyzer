"""
Generate a ranked raid scoreboard from curated Pokémon entries.

The script mirrors the heuristics used in the original spreadsheet-based
workflow and produces the same set of columns regardless of whether pandas is
installed. Invoke :func:`main` directly or import the helper functions into your
own scripts for more control over data filtering and presentation.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType

from pogo_analyzer import scoreboard as _scoreboard
from pogo_analyzer.data import PokemonRaidEntry
from pogo_analyzer.scoreboard import (
    RAID_ENTRIES,
    ExportResult,
    Row,
    ScoreboardExportConfig,
    SimpleTable,
    TableLike,
    calculate_iv_bonus,
    calculate_raid_score,
    iv_bonus,
    raid_score,
    score,
)
from pogo_analyzer.scoreboard import (
    add_priority_tier as _scoreboard_add_priority_tier,
)
from pogo_analyzer.scoreboard import (
    build_dataframe as _scoreboard_build_dataframe,
)
from pogo_analyzer.scoreboard import (
    build_entry_rows as _scoreboard_build_entry_rows,
)
from pogo_analyzer.scoreboard import (
    build_export_config as _scoreboard_build_export_config,
)
from pogo_analyzer.scoreboard import (
    build_rows as _scoreboard_build_rows,
)
from pogo_analyzer.scoreboard import (
    generate_scoreboard as _scoreboard_generate_scoreboard,
)

pd: ModuleType | None
try:  # Pandas provides richer output; fall back to a lightweight table otherwise.
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - exercised when pandas is absent.
    pd = None

# Re-export data helpers for compatibility with historical imports.
build_entry_rows = _scoreboard_build_entry_rows
build_rows = _scoreboard_build_rows


def _sync_pandas() -> None:
    """Mirror the current pandas availability into the shared scoreboard module."""

    _scoreboard.pd = pd


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Return parsed command-line arguments for :func:`main`."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory where CSV/Excel files should be written.",
    )
    parser.add_argument(
        "--csv-name",
        help="File name (or path) for the CSV export. Defaults to raid_scoreboard.csv.",
    )
    parser.add_argument(
        "--excel-name",
        help="File name (or path) for the Excel export. Defaults to raid_scoreboard.xlsx.",
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="Disable Excel export even when pandas is available.",
    )
    parser.add_argument(
        "--preview-limit",
        type=int,
        help="Number of rows to include in the console preview (default: 10).",
    )
    return parser.parse_args(argv)


def build_export_config(
    args: argparse.Namespace,
    env: Mapping[str, str] | None = None,
) -> ScoreboardExportConfig:
    """Proxy to :func:`pogo_analyzer.scoreboard.build_export_config`."""

    return _scoreboard_build_export_config(args, env=env)


def build_dataframe(
    entries: Sequence[PokemonRaidEntry] = RAID_ENTRIES,
) -> TableLike:
    """Construct a table using the shared scoreboard helpers with the current pandas state."""

    _sync_pandas()
    return _scoreboard_build_dataframe(entries)


def add_priority_tier(df: TableLike) -> TableLike:
    """Append priority tiers via the shared scoreboard helper."""

    return _scoreboard_add_priority_tier(df)


def generate_scoreboard(
    entries: Sequence[PokemonRaidEntry] = RAID_ENTRIES,
    *,
    config: ScoreboardExportConfig,
) -> ExportResult:
    """Build, rank, and persist the raid scoreboard using the shared helpers."""

    _sync_pandas()
    return _scoreboard_generate_scoreboard(entries, config=config)


def main(argv: Sequence[str] | None = None) -> ExportResult:
    """Command-line entry point for generating raid scoreboard exports."""

    args = parse_args(argv)
    try:
        config = build_export_config(args)
    except ValueError as exc:  # pragma: no cover - handled via CLI exit code.
        raise SystemExit(str(exc)) from exc

    result = generate_scoreboard(RAID_ENTRIES, config=config)

    print("Saved:", result.csv_path.resolve())
    if result.excel_path is None:
        print("Skipped Excel export: disabled via configuration.")
    elif result.excel_written:
        print("Saved:", result.excel_path.resolve())
    else:
        if result.excel_error == "pandas-missing":
            print("Skipped Excel export: install pandas to enable Excel output.")
        else:
            reason = result.excel_error or "unknown error"
            lower_reason = reason.lower()
            suggestion = ""
            if "openpyxl" in lower_reason:
                suggestion = " (install openpyxl)"
            elif "xlsxwriter" in lower_reason:
                suggestion = " (install xlsxwriter)"
            print(f"Warning: failed to write Excel{suggestion}. Reason:", reason)

    preview_limit = config.preview_limit
    print()
    print(f"Top {preview_limit} preview:")
    print(result.table.head(preview_limit).to_string(index=False))

    return result


__all__ = [
    "RAID_ENTRIES",
    "PokemonRaidEntry",
    "TableLike",
    "Row",
    "SimpleTable",
    "ScoreboardExportConfig",
    "ExportResult",
    "build_entry_rows",
    "build_rows",
    "add_priority_tier",
    "build_dataframe",
    "build_export_config",
    "generate_scoreboard",
    "parse_args",
    "calculate_iv_bonus",
    "calculate_raid_score",
    "iv_bonus",
    "raid_score",
    "score",
    "main",
]

if __name__ == "__main__":
    main()
