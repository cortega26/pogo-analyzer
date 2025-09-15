import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / 'src'))

from pogo_analyzer.data_loader import load_pokemon_stats
from pogo_analyzer.calculations import compute_stats, calc_cp, pvp_recommendation


def test_cp_dragonite_level40():
    stats_map = load_pokemon_stats()
    dragonite = stats_map['Dragonite']['Normal']
    eff = compute_stats(dragonite, (15, 15, 15), 40.0)
    cp = calc_cp(eff, eff['level'])
    assert cp == 3792


def test_pvp_recommendation_great_league():
    stats_map = load_pokemon_stats()
    bulba = stats_map['Bulbasaur']['Normal']
    rec = pvp_recommendation(bulba, (0, 15, 15))
    assert 'great' in rec
    assert rec['great']['cp'] <= 1500
    assert rec['great']['level'] <= 50
