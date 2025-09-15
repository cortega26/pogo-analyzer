from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class PokemonStats:
    """Base stats for a Pokémon form."""
    attack: int
    defense: int
    stamina: int


@dataclass
class PokemonForm:
    """Species form information with move pool."""
    name: str
    types: Tuple[str, Optional[str]]
    stats: PokemonStats
    fast_moves: List[str]
    charged_moves: List[str]


@dataclass
class PokemonInstance:
    """Represents an individual Pokémon with IVs and flags."""
    species: str
    form: str = "Normal"
    ivs: Tuple[int, int, int] = (0, 0, 0)
    level: float = 1.0
    cp: int = 10
    lucky: bool = False
    shadow: bool = False
    purified: bool = False
    best_buddy: bool = False
