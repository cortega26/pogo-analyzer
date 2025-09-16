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


if __name__ == "__main__":
    unittest.main()
