from math import floor, sqrt
from typing import Tuple

from .loader import load_cp_multipliers
from .models import PokemonStats


def calculate_cp(stats: PokemonStats, ivs: Tuple[int, int, int], level: float) -> int:
    """Calculate CP for given stats, IVs, and level."""
    multipliers = load_cp_multipliers()
    m = multipliers.get(level)
    if m is None:
        raise ValueError(f"Unknown CP multiplier for level {level}")
    atk = stats.attack + ivs[0]
    defense = stats.defense + ivs[1]
    stamina = stats.stamina + ivs[2]
    cp = floor((atk * sqrt(defense) * sqrt(stamina) * m * m) / 10)
    return max(cp, 10)
