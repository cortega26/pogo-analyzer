import math
import sys
from pathlib import Path

# Ensure project root on sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from pogodata import (
    load_pokemon_stats,
    load_pokemon_moves,
    load_cp_multipliers,
    load_type_effectiveness,
    calculate_cp,
    PokemonStats,
)


def test_load_pokemon_stats():
    stats = load_pokemon_stats()
    bulba = stats["Bulbasaur"]["Normal"]
    assert isinstance(bulba, PokemonStats)
    assert bulba.attack == 118
    assert bulba.defense == 111
    assert bulba.stamina == 128


def test_calculate_cp():
    stats = load_pokemon_stats()["Bulbasaur"]["Normal"]
    cp = calculate_cp(stats, (15, 15, 15), 20.0)
    assert cp == 637


def test_pokemon_moves():
    moves = load_pokemon_moves()
    bulba_moves = moves["Bulbasaur"]["Normal"]
    assert "Vine Whip" in bulba_moves["fast"]
    assert "Sludge Bomb" in bulba_moves["charged"]


def test_cp_multiplier_range():
    mult = load_cp_multipliers()
    assert 55.0 in mult
    assert math.isclose(mult[55.0], 0.86529999, rel_tol=1e-6)


def test_type_effectiveness():
    eff = load_type_effectiveness()
    assert eff["Grass"]["Water"] > 1
    assert eff["Grass"]["Fire"] < 1
