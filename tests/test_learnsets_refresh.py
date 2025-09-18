"""Tests for the learnsets normaliser CLI."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from pogo_analyzer.learnsets_refresh import main as learnsets_main


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_learnsets_refresh_csv_to_json(tmp_path: Path) -> None:
    moves_in = tmp_path / "moves.json"
    _write_json(
        moves_in,
        {
            "fast": [{"name": "Snarl", "damage": 5, "energy_gain": 13, "turns": 4}],
            "charge": [{"name": "Brutal Swing", "damage": 65, "energy_cost": 40}],
        },
    )

    map_in = tmp_path / "map.csv"
    with map_in.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["species", "fast", "charge"])
        writer.writerow(["Hydreigon", "Snarl", "Brutal Swing"])

    out_path = tmp_path / "learnsets.json"
    result = learnsets_main(["--moves-in", str(moves_in), "--map-in", str(map_in), "--out", str(out_path)])
    assert result.exists()
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["Hydreigon"]["fast"] == ["Snarl"]
    assert payload["Hydreigon"]["charge"] == ["Brutal Swing"]


def test_learnsets_refresh_rejects_unknown_move(tmp_path: Path) -> None:
    moves_in = tmp_path / "moves.json"
    _write_json(moves_in, {"fast": [], "charge": []})
    out_path = tmp_path / "learnsets.json"

    map_in = tmp_path / "map.csv"
    with map_in.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["species", "fast", "charge"])
        writer.writerow(["Hydreigon", "Snarl", "Brutal Swing"])

    with pytest.raises(ValueError):
        learnsets_main(["--moves-in", str(moves_in), "--map-in", str(map_in), "--out", str(out_path)])

