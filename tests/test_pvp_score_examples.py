"""Regression tests for PvP score calculations against known builds."""

from __future__ import annotations

import pytest

from pogo_analyzer.formulas import effective_stats, infer_level_from_cp
from pogo_analyzer.pvp import PvpChargeMove, PvpFastMove, compute_pvp_score


@pytest.fixture(scope="module")
def hydreigon_build() -> tuple[float, float, int]:
    level, _ = infer_level_from_cp(256, 188, 216, 15, 15, 15, 3325)
    attack, defense, hp = effective_stats(256, 188, 216, 15, 15, 15, level)
    return attack, defense, hp


@pytest.fixture(scope="module")
def hydreigon_moves() -> tuple[PvpFastMove, list[PvpChargeMove]]:
    fast = PvpFastMove("Snarl", damage=5, energy_gain=13, turns=4)
    charge = PvpChargeMove("Brutal Swing", damage=65, energy_cost=40)
    return fast, [charge]


def test_compute_pvp_score_matches_reference(
    hydreigon_build: tuple[float, float, int], hydreigon_moves: tuple[PvpFastMove, list[PvpChargeMove]]
) -> None:
    attack, defense, hp = hydreigon_build
    fast_move, charge_moves = hydreigon_moves

    result = compute_pvp_score(
        attack,
        defense,
        hp,
        fast_move,
        charge_moves,
        league="great",
        beta=0.52,
    )

    assert result["stat_product"] == pytest.approx(5_392_483.542653858, rel=1e-12)
    assert result["stat_product_normalised"] == pytest.approx(3.370302214158661, rel=1e-12)
    assert result["move_pressure"] == pytest.approx(6.4, rel=1e-12)
    assert result["move_pressure_normalised"] == pytest.approx(0.13333333333333333, rel=1e-12)
    assert result["score"] == pytest.approx(0.7150861940536062, rel=1e-12)
