"""Golden tests for PvE rotation scoring helpers."""

from __future__ import annotations

from collections import Counter

import pytest

from pogo_analyzer.formulas import effective_stats, infer_level_from_cp
from pogo_analyzer.pve import ChargeMove, FastMove, compute_pve_score, rotation_dps


@pytest.fixture(scope="module")
def hydreigon_build() -> tuple[float, float, int]:
    level, _ = infer_level_from_cp(256, 188, 216, 15, 15, 15, 3325)
    attack, defense, hp = effective_stats(256, 188, 216, 15, 15, 15, level)
    return attack, defense, hp


@pytest.fixture(scope="module")
def hydreigon_moves() -> tuple[FastMove, list[ChargeMove]]:
    fast = FastMove("Snarl", power=12, energy_gain=13, duration=1.0, stab=True)
    charge = ChargeMove("Brutal Swing", power=65, energy_cost=40, duration=1.9, stab=True)
    return fast, [charge]


def test_rotation_dps_matches_cli_example(
    hydreigon_build: tuple[float, float, int], hydreigon_moves: tuple[FastMove, list[ChargeMove]]
) -> None:
    attack, _, _ = hydreigon_build
    fast_move, charge_moves = hydreigon_moves

    result = rotation_dps(fast_move, charge_moves, attack, 180.0)

    assert result == pytest.approx(14.605873261205565, rel=1e-9)


def test_compute_pve_score_hydreigon_example(
    hydreigon_build: tuple[float, float, int], hydreigon_moves: tuple[FastMove, list[ChargeMove]]
) -> None:
    attack, defense, hp = hydreigon_build
    fast_move, charge_moves = hydreigon_moves

    score = compute_pve_score(
        attack,
        defense,
        hp,
        fast_move,
        charge_moves,
        target_defense=180.0,
        incoming_dps=35.0,
        alpha=0.6,
    )

    assert score["dps"] == pytest.approx(14.605873261205565, rel=1e-9)
    assert score["cycle_damage"] == pytest.approx(72.6923076923077, rel=1e-9)
    assert score["cycle_time"] == pytest.approx(4.976923076923077, rel=1e-9)
    assert score["fast_moves_per_cycle"] == pytest.approx(3.0769230769230766, rel=1e-9)
    assert score["charge_usage_per_cycle"] == Counter({"Brutal Swing": 1})
    assert score["ehp"] == pytest.approx(146.86162664342945, rel=1e-9)
    assert score["tdo"] == pytest.approx(61.286923019669175, rel=1e-9)
    assert score["value"] == pytest.approx(25.921709769448622, rel=1e-9)
