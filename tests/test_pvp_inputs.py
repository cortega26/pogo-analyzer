"""Input validation tests for PvP scoring."""

from __future__ import annotations

import pytest

from pogo_analyzer.pvp import (
    DEFAULT_LEAGUE_CONFIGS,
    PvpChargeMove,
    PvpFastMove,
    compute_pvp_score,
    normalise,
)


def test_invalid_league_key_and_beta_reference_checks() -> None:
    fast = PvpFastMove("Mud Shot", damage=3, energy_gain=9, turns=1)
    charge = PvpChargeMove("Earthquake", damage=120, energy_cost=65)

    with pytest.raises(KeyError):
        compute_pvp_score(120.0, 120.0, 150, fast, [charge], league="mythic")

    with pytest.raises(ValueError):
        compute_pvp_score(120.0, 120.0, 150, fast, [charge], beta=1.0)

    with pytest.raises(ValueError):
        normalise(100.0, 0.0)


def test_invalid_shield_weights_length_raises() -> None:
    fast = PvpFastMove("Counter", damage=4, energy_gain=8, turns=2)
    charge = PvpChargeMove("Close Combat", damage=100, energy_cost=45)

    with pytest.raises(ValueError):
        compute_pvp_score(
            130.0,
            130.0,
            160,
            fast,
            [charge],
            shield_weights=[1.0, 0.0],  # invalid length
        )


def test_cmp_threshold_not_met_applies_no_bonus() -> None:
    fast = PvpFastMove("Dragon Breath", damage=4, energy_gain=3, turns=1)
    charge = PvpChargeMove("Dragon Claw", damage=50, energy_cost=35)

    res = compute_pvp_score(
        140.0,
        140.0,
        160,
        fast,
        [charge],
        league="great",
        cmp_percentile=0.5,
        cmp_threshold=0.7,
        cmp_eta=0.02,
        league_configs=DEFAULT_LEAGUE_CONFIGS,
    )
    assert "cmp_bonus" not in res["modifiers"]

