"""Tests for IV optimization mode in PvP scoreboard generator."""

from __future__ import annotations

import csv
import json
from pathlib import Path

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
                {"name": "Hydreigon", "base_attack": 256, "base_defense": 188, "base_stamina": 211}
            ]
        },
    )
    _write_json(
        moves,
        {
            "fast": [{"name": "Snarl", "damage": 5, "energy_gain": 13, "turns": 4}],
            "charge": [{"name": "Brutal Swing", "damage": 65, "energy_cost": 40}],
        },
    )
    _write_json(learnsets, {"Hydreigon": {"fast": ["Snarl"], "charge": ["Brutal Swing"]}})
    return species, moves, learnsets


def _levels_from_csv(csv_path: Path) -> list[str]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row.get("Level", "") for row in reader]


def test_iv_optimization_changes_level_or_score(tmp_path: Path) -> None:
    species, moves, learnsets = _mini_dataset(tmp_path)
    base = psg.main(["--species", str(species), "--moves", str(moves), "--learnsets", str(learnsets), "--league-cap", "1500"])
    opt = psg.main([
        "--species", str(species), "--moves", str(moves), "--learnsets", str(learnsets), "--league-cap", "1500",
        "--iv-mode", "max-sp",
    ])

    base_levels = _levels_from_csv(base)
    opt_levels = _levels_from_csv(opt)
    assert base_levels != opt_levels or base.read_text() != opt.read_text()

