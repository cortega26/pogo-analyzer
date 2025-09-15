from dataclasses import dataclass
from typing import Optional


@dataclass
class PokemonSpecies:
    """Species stats and identifiers."""
    pokemon_id: int
    name: str
    form: str
    base_attack: int
    base_defense: int
    base_stamina: int


@dataclass
class Move:
    """Move data."""
    move_id: int
    name: str
    type: str
    power: int
    energy_delta: int
    duration: int
    is_fast: bool


@dataclass
class CPMultiplier:
    """CP multiplier for a level."""
    level: float
    multiplier: float
