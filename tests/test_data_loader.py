import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / 'src'))

from pogo_analyzer.data_loader import (
    load_pokemon_stats,
    load_moves,
    load_pokemon_moves,
    load_cp_multipliers,
    load_type_effectiveness,
    SHADOW_ATTACK_MULT,
    LEAGUE_CP_CAPS,
)
from pogo_analyzer.models import PokemonSpecies, Move


def test_load_pokemon_stats():
    stats = load_pokemon_stats()
    bulba = stats['Bulbasaur']['Normal']
    assert isinstance(bulba, PokemonSpecies)
    assert bulba.base_attack == 118


def test_load_moves():
    moves = load_moves()
    vine = moves['Vine Whip']
    assert isinstance(vine, Move)
    assert vine.power == 6
    assert vine.is_fast


def test_constants_and_multipliers():
    mult = load_cp_multipliers()
    assert 1.0 in mult
    assert SHADOW_ATTACK_MULT > 1
    assert LEAGUE_CP_CAPS['great'] == 1500


def test_type_effectiveness():
    eff = load_type_effectiveness()
    assert eff['Grass']['Water'] > 1
