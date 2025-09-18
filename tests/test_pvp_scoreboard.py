"""Tests for the PvP scoreboard generator CLI."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import pvp_scoreboard_generator as psg


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _mini_dataset(tmp_path: Path) -> tuple[Path, Path, Path]:
    species = tmp_path / "species.json"
    moves = tmp_path / "moves.json"
    learnsets = tmp_path / "learnsets.json"

    _write_json(
        species,
        {
            "species": [
                {"name": "Hydreigon", "base_attack": 256, "base_defense": 188, "base_stamina": 211},
                {"name": "Azumarill", "base_attack": 112, "base_defense": 152, "base_stamina": 225},
            ]
        },
    )
    _write_json(
        moves,
        {
            "fast": [
                {"name": "Snarl", "damage": 5, "energy_gain": 13, "turns": 4},
                {"name": "Bubble", "damage": 2, "energy_gain": 11, "turns": 3},
            ],
            "charge": [
                {"name": "Brutal Swing", "damage": 65, "energy_cost": 40},
                {"name": "Play Rough", "damage": 90, "energy_cost": 60},
            ],
        },
    )
    _write_json(
        learnsets,
        {
            "Hydreigon": {"fast": ["Snarl"], "charge": ["Brutal Swing"]},
            "Azumarill": {"fast": ["Bubble"], "charge": ["Play Rough"]},
        },
    )
    return species, moves, learnsets


def test_pvp_scoreboard_writes_csv(tmp_path: Path) -> None:
    species, moves, learnsets = _mini_dataset(tmp_path)
    out = tmp_path / "out"
    csv_path = psg.main(
        [
            "--species",
            str(species),
            "--moves",
            str(moves),
            "--learnsets",
            str(learnsets),
            "--output-dir",
            str(out),
            "--league-cap",
            "1500",
        ]
    )
    assert csv_path.exists()
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        assert {"Species", "Score", "Best Fast", "Best Charge 1"}.issubset(set(header))
        rows = list(reader)
        assert rows, "expected at least one row in pvp scoreboard"


def test_pvp_scoreboard_unknown_move_in_learnsets(tmp_path: Path) -> None:
    species, moves, learnsets = _mini_dataset(tmp_path)
    broken = json.loads(learnsets.read_text(encoding="utf-8"))
    broken["Hydreigon"]["charge"] = ["Nonexistent"]
    learnsets.write_text(json.dumps(broken), encoding="utf-8")

    with pytest.raises(SystemExit):
        psg.main([
            "--species", str(species), "--moves", str(moves), "--learnsets", str(learnsets)
        ])


def test_pvp_scoreboard_unsupported_league_cap(tmp_path: Path) -> None:
    species, moves, learnsets = _mini_dataset(tmp_path)
    with pytest.raises(SystemExit):
        psg.main([
            "--species", str(species), "--moves", str(moves), "--learnsets", str(learnsets), "--league-cap", "1234"
        ])

