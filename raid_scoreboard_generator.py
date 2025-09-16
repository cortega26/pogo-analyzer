"""
Generate a ranked raid scoreboard from curated Pokémon entries.

The script mirrors the heuristics used in the original spreadsheet-based
workflow and produces the same set of columns regardless of whether pandas is
installed. Invoke :func:`main` directly or import the helper functions into your
own scripts for more control over data filtering and presentation.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

try:  # Pandas provides richer output; fall back to a lightweight table otherwise.
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - exercised when pandas is absent.
    pd = None  # type: ignore[assignment]

from pogo_analyzer.data import DEFAULT_RAID_ENTRIES, PokemonRaidEntry, build_entry_rows
from pogo_analyzer.scoring import (
    calculate_iv_bonus,
    calculate_raid_score,
    iv_bonus,
    raid_score,
)
from pogo_analyzer.tables import Row, SimpleTable

RAID_ENTRIES = DEFAULT_RAID_ENTRIES
build_rows = build_entry_rows

# Backwards-compatibility alias: historical name retained for callers.
score = raid_score


def _as_table(rows: Sequence[Row]):
    """Return a pandas DataFrame or :class:`SimpleTable` depending on availability."""

    if pd is not None:
        return pd.DataFrame(rows)
    return SimpleTable(rows)


def build_dataframe(entries: Sequence[PokemonRaidEntry] = RAID_ENTRIES):
    """Construct a tabular object from raid entries.

    Parameters
    ----------
    entries:
        Iterable of :class:`PokemonRaidEntry` instances. Defaults to the bundled
        dataset but you can supply your own selection to customise the output.

    Returns
    -------
    DataFrame | SimpleTable
        ``pandas.DataFrame`` when pandas is installed, otherwise
        :class:`~pogo_analyzer.simple_table.SimpleTable`.
    """

    rows = build_entry_rows(entries)
    return _as_table(rows)


def add_priority_tier(df):
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


def main() -> None:
    """Command-line entry point for generating raid scoreboard exports."""

    df = build_dataframe()
    df = df.sort_values(by="Raid Score (1-100)", ascending=False).reset_index(drop=True)
    df = add_priority_tier(df)
    out_csv = Path("raid_scoreboard.csv")
    out_xlsx = Path("raid_scoreboard.xlsx")

    # Save CSV
    df.to_csv(out_csv, index=False)
    # Save Excel (requires pandas with an Excel engine installed)
    if isinstance(df, SimpleTable) or pd is None:
        print("Skipped Excel export: install pandas to enable Excel output.")
    else:
        try:
            df.to_excel(out_xlsx, index=False)
            print("Saved:", out_xlsx.resolve())
        except Exception as e:
            reason = str(e)
            lower_reason = reason.lower()
            suggestion = ""
            if "openpyxl" in lower_reason:
                suggestion = " (install openpyxl)"
            elif "xlsxwriter" in lower_reason:
                suggestion = " (install xlsxwriter)"
            print(f"Warning: failed to write Excel{suggestion}. Reason:", reason)
    print("Saved:", out_csv.resolve())
    print()
    print("Top 10 preview:")
    print(df.head(10).to_string(index=False))


__all__ = [
    "RAID_ENTRIES",
    "PokemonRaidEntry",
    "Row",
    "SimpleTable",
    "build_entry_rows",
    "build_rows",
    "add_priority_tier",
    "build_dataframe",
    "calculate_iv_bonus",
    "calculate_raid_score",
    "iv_bonus",
    "raid_score",
    "score",
    "main",
]


if __name__ == "__main__":
    main()
