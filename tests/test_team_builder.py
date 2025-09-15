import json
from pathlib import Path

import pytest

from pogo_analyzer.team_builder import (
    Roster,
    Team,
    read_roster_data,
    write_roster_data,
)


def test_read_write_helpers(tmp_path):
    path = tmp_path / "teams.json"
    assert read_roster_data(path) == {}

    payload = {"Alpha": {"members": []}}
    write_roster_data(payload, path)
    assert json.loads(path.read_text()) == payload
    assert read_roster_data(path) == payload


def test_roster_persists_members(tmp_path):
    path = tmp_path / "teams.json"
    roster = Roster.load(path)
    roster.create_team("Alpha")
    roster.add_member("Alpha", species="Bulbasaur", form="Normal", ivs=(0, 0, 0), level=1.0)

    reloaded = Roster.load(path)
    team = reloaded.get_team("Alpha")
    assert len(team.members) == 1
    member = team.members[0]
    assert member["species"] == "Bulbasaur"
    assert member["ivs"] == [0, 0, 0]
    assert member["form"] == "Normal"


def test_recommendation_prefers_high_stat_product(tmp_path):
    path = tmp_path / "teams.json"
    roster = Roster.load(path)
    roster.create_team("Alpha")
    roster.add_member("Alpha", species="Bulbasaur", ivs=(0, 0, 0), level=1.0)
    roster.add_member("Alpha", species="Charmander", ivs=(15, 15, 15), level=20.0)

    recommendation = roster.recommend("Alpha", "great")
    best = recommendation["analysis"]
    stat_products = [member["pvp"]["great"]["stat_product"] for member in recommendation["members"]]

    assert recommendation["team"] == "Alpha"
    assert recommendation["league"] == "great"
    assert recommendation["best_member"] == "Charmander"
    assert best["name"] == "Charmander"
    assert best["pvp"]["great"]["stat_product"] == max(stat_products)


def test_recommendation_requires_members():
    team = Team("Empty")
    with pytest.raises(ValueError):
        team.recommend_for_league("great")
    with pytest.raises(ValueError):
        team.recommend_for_league("invalid")
