"""Load and update static Pokémon Go data files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.request import urlopen

from .models import PokemonStats, PokemonForm

# Directory containing JSON data files
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

POGOAPI = "https://pogoapi.net/api/v1"
ENDPOINTS = {
    "pokemon_stats": "pokemon_stats.json",
    "fast_moves": "fast_moves.json",
    "charged_moves": "charged_moves.json",
    "type_effectiveness": "type_effectiveness.json",
    "cp_multipliers": "cp_multiplier.json",
}


def _download(url: str) -> str:
    with urlopen(url) as resp:  # nosec - read-only public data
        return resp.read().decode("utf-8")


def update_data(data_dir: Path = DATA_DIR) -> None:
    """Download latest reference data into ``data_dir``.

    This fetches from the public pogoapi.net endpoints and writes the JSON files.
    CP multipliers are extended to level 55 for best-buddy calculations.
    """
    data_dir.mkdir(exist_ok=True)
    for key, endpoint in ENDPOINTS.items():
        text = _download(f"{POGOAPI}/{endpoint}")
        path = data_dir / endpoint
        path.write_text(text)
        if key == "cp_multipliers":
            # Extend to level 55 if necessary
            data = json.loads(text)
            if data[-1]["level"] < 55:
                step = data[-1]["multiplier"] - data[-2]["multiplier"]
                level = data[-1]["level"]
                mult = data[-1]["multiplier"]
                while level < 55:
                    level = round(level + 0.5, 1)
                    mult = round(mult + step, 8)
                    data.append({"level": level, "multiplier": mult})
                path.write_text(json.dumps(data, indent=4))


def load_json(name: str, data_dir: Path = DATA_DIR):
    return json.loads((data_dir / name).read_text())


def load_pokemon_stats(data_dir: Path = DATA_DIR) -> Dict[str, Dict[str, PokemonStats]]:
    raw = load_json("pokemon_stats.json", data_dir)
    stats: Dict[str, Dict[str, PokemonStats]] = {}
    for entry in raw:
        name = entry["pokemon_name"]
        form = entry.get("form", "Normal")
        stats.setdefault(name, {})[form] = PokemonStats(
            attack=entry["base_attack"],
            defense=entry["base_defense"],
            stamina=entry["base_stamina"],
        )
    return stats


def load_move_data(data_dir: Path = DATA_DIR) -> Dict[str, Dict[str, Dict]]:
    fast = load_json("fast_moves.json", data_dir)
    charged = load_json("charged_moves.json", data_dir)
    move_map: Dict[str, Dict] = {}
    for m in fast + charged:
        move_map[m["name"]] = m
    return {"moves": move_map}


def load_pokemon_moves(data_dir: Path = DATA_DIR) -> Dict[str, Dict[str, List[str]]]:
    raw = load_json("pokemon_moves.json", data_dir)
    out: Dict[str, Dict[str, List[str]]] = {}
    for entry in raw:
        name = entry["pokemon_name"]
        form = entry.get("form", "Normal")
        out.setdefault(name, {})[form] = {
            "fast": entry["fast_moves"],
            "charged": entry["charged_moves"],
        }
    return out


def load_cp_multipliers(data_dir: Path = DATA_DIR) -> Dict[float, float]:
    raw = load_json("cp_multipliers.json", data_dir)
    return {entry["level"]: entry["multiplier"] for entry in raw}


def load_type_effectiveness(data_dir: Path = DATA_DIR) -> Dict[str, Dict[str, float]]:
    return load_json("type_effectiveness.json", data_dir)
