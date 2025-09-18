"""Smoke test: default scoreboard export writes a valid CSV with core columns."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

import raid_scoreboard_generator as rsg


def test_scoreboard_smoke_csv_has_core_columns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAID_SCOREBOARD_DISABLE_EXCEL", "1")

    result = rsg.main(argv=[])
    assert result is not None

    csv_path = result.csv_path
    assert csv_path.exists() and csv_path.suffix == ".csv"

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

    # Minimal set of core columns expected by consumers
    expected = {"Your Pokémon", "Final Raid Form", "Primary Role", "Raid Score (1-100)"}
    assert expected.issubset(set(header))

