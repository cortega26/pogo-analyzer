"""High level Pokémon analysis functions."""
from __future__ import annotations

from typing import Dict, Tuple

from . import data_loader, calculations
from .models import PokemonSpecies, Move


def analyze_pokemon(
    name: str,
    form: str,
    ivs: Tuple[int, int, int],
    level: float,
    *,
    shadow: bool = False,
    purified: bool = False,
    best_buddy: bool = False,
) -> Dict:
    stats_map = data_loader.load_pokemon_stats()
    moves_map = data_loader.load_pokemon_moves()
    move_data = data_loader.load_moves()

    species: PokemonSpecies = stats_map[name][form]
    stats = calculations.compute_stats(
        species, ivs, level, shadow=shadow, purified=purified, buddy=best_buddy
    )
    cp = calculations.calc_cp(stats, stats["level"])

    moves = moves_map[name][form]
    fast_move: Move = move_data[moves["fast"][0]]
    charged_move: Move = move_data[moves["charged"][0]]
    pve_bp = calculations.pve_breakpoints(stats, fast_move, boss_def=200)
    pve_sc = calculations.pve_score(stats, {"fast": fast_move, "charged": charged_move})
    pvp_rec = calculations.pvp_recommendation(species, ivs)
    return {
        "name": name,
        "form": form,
        "level": stats["level"],
        "cp": cp,
        "pve": {"breakpoints": pve_bp, "score": pve_sc},
        "pvp": pvp_rec,
    }
