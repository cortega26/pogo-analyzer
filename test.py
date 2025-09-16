"""Tests for raid_scoreboard_generator."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
from pathlib import Path

import unittest

import raid_scoreboard_generator as rsg


class ChangeDirectory:
    """Context manager to temporarily switch working directory."""

    def __init__(self, target: Path):
        self._target = target
        self._previous: Path | None = None

    def __enter__(self) -> Path:
        self._previous = Path.cwd()
        os.chdir(self._target)
        return self._target

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        if self._previous is not None:
            os.chdir(self._previous)


class RaidScoreboardTests(unittest.TestCase):
    def test_missing_pandas_skips_excel_export(self) -> None:
        """Ensure the user guidance is correct when pandas isn't available."""

        original_pd = rsg.pd
        try:
            rsg.pd = None
            with tempfile.TemporaryDirectory() as tmp:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    with ChangeDirectory(Path(tmp)):
                        rsg.main()
                out_text = output.getvalue()
                self.assertIn("pandas", out_text)
                self.assertNotIn("openpyxl", out_text)
                self.assertTrue(Path(tmp, "raid_scoreboard.csv").exists())
                self.assertFalse(Path(tmp, "raid_scoreboard.xlsx").exists())
        finally:
            rsg.pd = original_pd

    def test_simple_table_column_management(self) -> None:
        """SimpleTable should preserve column order and support new columns."""

        rows = [{"a": 1, "b": 2}, {"b": 3, "c": 4}]
        table = rsg.SimpleTable(rows)

        # Columns discovered in order of appearance with fallbacks filled in.
        self.assertEqual(table._columns, ["a", "b", "c"])  # type: ignore[attr-defined]
        self.assertEqual(table._rows[0]["c"], "")  # type: ignore[attr-defined]

        # Adding a new column should append it only once.
        table["d"] = [5, 6]
        self.assertEqual(table._columns, ["a", "b", "c", "d"])  # type: ignore[attr-defined]
        self.assertEqual([row["d"] for row in table._rows], [5, 6])  # type: ignore[attr-defined]

    def test_pokemon_entry_row_generation(self) -> None:
        """PokemonRaidEntry should format names, IVs, and scores consistently."""

        entry = rsg.PokemonRaidEntry(
            "Tester",
            (15, 14, 13),
            final_form="Mega Tester",
            role="Support",
            base=81,
            lucky=True,
            shadow=True,
            needs_tm=True,
            mega_soon=True,
            notes="Example entry for unit tests.",
        )
        row = entry.as_row()
        expected_score = rsg.raid_score(
            81,
            rsg.iv_bonus(15, 14, 13),
            lucky=True,
            needs_tm=True,
            mega_bonus_soon=True,
            mega_bonus_now=False,
        )
        self.assertEqual(row["Your Pokémon"], "Tester (lucky) (shadow)")
        self.assertEqual(row["IV (Atk/Def/Sta)"], "15/14/13")
        self.assertEqual(row["Move Needs (CD/ETM?)"], "Yes")
        self.assertEqual(row["Mega Available"], "Soon")
        self.assertEqual(row["Raid Score (1-100)"], expected_score)

    def test_build_dataframe_allows_custom_entries(self) -> None:
        """Custom entry sequences should build into data frames or tables."""

        entry = rsg.PokemonRaidEntry(
            "Solo",
            (10, 11, 12),
            final_form="Final",
            role="Utility",
            base=70,
            notes="Single test entry.",
        )
        df = rsg.build_dataframe([entry])
        if isinstance(df, rsg.SimpleTable):
            data_row = df._rows[0]  # type: ignore[attr-defined]
        else:
            data_row = df.iloc[0].to_dict()
        self.assertEqual(data_row["Your Pokémon"], "Solo")
        self.assertEqual(data_row["Final Raid Form"], "Final")
        self.assertEqual(data_row["Primary Role"], "Utility")

    def test_add_priority_tier_assigns_expected_labels(self) -> None:
        """Threshold boundaries should map onto documented priority tiers."""

        table = rsg.SimpleTable(
            [
                {"Raid Score (1-100)": 90.0},
                {"Raid Score (1-100)": 86.0},
                {"Raid Score (1-100)": 78.0},
                {"Raid Score (1-100)": 70.0},
                {"Raid Score (1-100)": 65.0},
            ]
        )
        tiered = rsg.add_priority_tier(table)
        tiers = [row["Priority Tier"] for row in tiered._rows]  # type: ignore[attr-defined]
        self.assertEqual(
            tiers,
            [
                "S (Build ASAP)",
                "A (High)",
                "B (Good)",
                "C (Situational)",
                "D (Doesn't belong on a Raids list)",
            ],
        )


if __name__ == "__main__":
    unittest.main()
