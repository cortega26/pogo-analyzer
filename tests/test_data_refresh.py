"""Tests for the offline data refresh normaliser CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pogo_analyzer.data_refresh import main as data_refresh_main


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_data_refresh_writes_normalised_outputs(tmp_path: Path) -> None:
    species_in = tmp_path / "species.json"
    moves_in = tmp_path / "moves.json"
    out_dir = tmp_path / "out"

    _write_json(
        species_in,
        {
            "species": [
                {"name": "Hydreigon", "base_attack": 256, "base_defense": 188, "base_stamina": 211},
                {"name": "Azumarill", "base_attack": 112, "base_defense": 152, "base_stamina": 225},
            ]
        },
    )
    _write_json(
        moves_in,
        {
            "fast": [
                {"name": "Snarl", "damage": 5, "energy_gain": 13, "turns": 4},
                {"name": "Bubble", "damage": 2, "energy_gain": 11, "turns": 3},
            ],
            "charge": [
                {"name": "Brutal Swing", "damage": 65, "energy_cost": 40},
                {"name": "Play Rough", "damage": 90, "energy_cost": 60, "reliability": 0.02, "has_buff": False},
            ],
        },
    )

    species_out, moves_out = data_refresh_main(
        [
            "--species-in",
            str(species_in),
            "--moves-in",
            str(moves_in),
            "--out-dir",
            str(out_dir),
            "--prefix",
            "normalized",
            "--source-tag",
            "pytest",
        ]
    )

    assert species_out.exists()
    assert moves_out.exists()

    s = json.loads(species_out.read_text(encoding="utf-8"))
    m = json.loads(moves_out.read_text(encoding="utf-8"))

    assert s["metadata"]["source"] == "pytest"
    assert len(s["species"]) == 2
    assert {k for k in s["species"][0].keys()} == {"name", "base_attack", "base_defense", "base_stamina"}

    assert m["metadata"]["source"] == "pytest"
    assert len(m["fast"]) == 2
    assert len(m["charge"]) == 2


def test_data_refresh_rejects_bad_species(tmp_path: Path) -> None:
    species_in = tmp_path / "species.json"
    moves_in = tmp_path / "moves.json"
    _write_json(species_in, {"species": [{"name": "", "base_attack": 1, "base_defense": 1, "base_stamina": 1}]})
    _write_json(moves_in, {"fast": [], "charge": []})

    with pytest.raises(ValueError):
        data_refresh_main(["--species-in", str(species_in), "--moves-in", str(moves_in)])


def test_data_refresh_rejects_bad_moves(tmp_path: Path) -> None:
    species_in = tmp_path / "species.json"
    moves_in = tmp_path / "moves.json"
    _write_json(species_in, {"species": [{"name": "X", "base_attack": 1, "base_defense": 1, "base_stamina": 1}]})
    _write_json(moves_in, {"fast": [{"name": "A", "damage": -1, "energy_gain": 9, "turns": 1}], "charge": []})

    with pytest.raises(ValueError):
        data_refresh_main(["--species-in", str(species_in), "--moves-in", str(moves_in)])

