"""Availability penalty clamping for PvP scoring."""

from __future__ import annotations

import pytest

from pogo_analyzer.pvp import PvpChargeMove, PvpFastMove, compute_pvp_score


def test_pvp_availability_penalty_clamped() -> None:
    fast = PvpFastMove("Vine Whip", damage=3, energy_gain=8, turns=2)
    charge = PvpChargeMove("Frenzy Plant", damage=100, energy_cost=45, has_buff=True)
    res = compute_pvp_score(
        130.0,
        130.0,
        160,
        fast,
        [charge],
        league="great",
        availability_penalty=5.0,  # will be clamped to 0.99
    )
    mods = res["modifiers"]
    assert 0.0 < mods.get("availability_penalty", 1.0) < 1.0

