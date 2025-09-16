"""Load static Pokémon GO reference data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .models import PokemonSpecies, Move, CPMultiplier

# Directory containing JSON data files
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Constants
SHADOW_ATTACK_MULT = 1.2
SHADOW_DEFENSE_MULT = 0.833
PURIFIED_ATTACK_BONUS = 0
PURIFIED_DEFENSE_MULT = 1.0
BEST_BUDDY_LEVEL_BONUS = 1.0
LEAGUE_CP_CAPS = {"great": 1500, "ultra": 2500, "master": 10000}


def _load_json(name: str) -> Any:
    return json.loads((DATA_DIR / name).read_text())


def load_pokemon_stats() -> Dict[str, Dict[str, PokemonSpecies]]:
    raw = _load_json("pokemon_stats.json")
    out: Dict[str, Dict[str, PokemonSpecies]] = {}
    for entry in raw:
        species = PokemonSpecies(
            pokemon_id=entry["pokemon_id"],
            name=entry["pokemon_name"],
            form=entry.get("form", "Normal"),
            base_attack=entry["base_attack"],
            base_defense=entry["base_defense"],
            base_stamina=entry["base_stamina"],
        )
        out.setdefault(species.name, {})[species.form] = species
    return out


def load_moves() -> Dict[str, Move]:
    fast = _load_json("fast_moves.json")
    charged = _load_json("charged_moves.json")
    moves: Dict[str, Move] = {}
    for entry in fast:
        moves[entry["name"]] = Move(
            move_id=entry["move_id"],
            name=entry["name"],
            type=entry["type"],
            power=entry.get("power", 0),
            energy_delta=entry.get("energy_delta", 0),
            duration=entry.get("duration", 0),
            is_fast=True,
        )
    for entry in charged:
        moves[entry["name"]] = Move(
            move_id=entry["move_id"],
            name=entry["name"],
            type=entry["type"],
            power=entry.get("power", 0),
            energy_delta=entry.get("energy_delta", 0),
            duration=entry.get("duration", 0),
            is_fast=False,
        )
    return moves


def load_pokemon_moves() -> Dict[str, Dict[str, Dict[str, List[str]]]]:
    raw = _load_json("pokemon_moves.json")
    out: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
    for entry in raw:
        name = entry["pokemon_name"]
        form = entry.get("form", "Normal")
        out.setdefault(name, {})[form] = {
            "fast": entry["fast_moves"],
            "charged": entry["charged_moves"],
        }
    return out


def load_cp_multipliers() -> Dict[float, float]:
    raw = _load_json("cp_multipliers.json")
    return {entry["level"]: entry["multiplier"] for entry in raw}


def load_type_effectiveness() -> Dict[str, Dict[str, float]]:
    return {k: v for k, v in _load_json("type_effectiveness.json").items()}
