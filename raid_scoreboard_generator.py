"""
Raid Scoreboard Generator
-------------------------
This script builds a sortable raid value scoreboard for your listed Pokémon,
scoring each entry on a 1–100 scale based on:
- Species baseline (final raid form & meta placement)
- IV contribution (Atk-weighted for raids)
- Lucky cost efficiency
- Move requirements (Community Day / Elite TM)
- Mega availability (now/soon) for team boost utility

Outputs:
- Console preview (head of table)
- CSV at ./raid_scoreboard.csv with full data
- Excel at ./raid_scoreboard.xlsx with full data

Notes:
- This is a guide heuristic, not a simulator. Use it to set priorities quickly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

try:  # Pandas provides richer output; fall back to a lightweight table otherwise.
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - exercised when pandas is absent.
    pd = None  # type: ignore[assignment]

from pogo_analyzer.raid_entries import RAID_ENTRIES, PokemonRaidEntry, build_rows
from pogo_analyzer.scoring import iv_bonus, raid_score
from pogo_analyzer.simple_table import Row, SimpleTable

# Backwards-compatibility alias: historical name retained for callers.
score = raid_score


def _as_table(rows: Sequence[Row]):
    if pd is not None:
        return pd.DataFrame(rows)
    return SimpleTable(rows)


def build_dataframe(entries: Sequence[PokemonRaidEntry] = RAID_ENTRIES):
    """Construct a table for the provided raid entries."""

    rows = build_rows(entries)
    return _as_table(rows)


def add_priority_tier(df):
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
    "add_priority_tier",
    "build_dataframe",
    "iv_bonus",
    "raid_score",
    "score",
    "main",
]


if __name__ == "__main__":
    main()
