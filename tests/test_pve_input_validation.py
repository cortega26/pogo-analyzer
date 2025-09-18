"""Input validation tests for PvE scoring."""

from __future__ import annotations

import pytest

from pogo_analyzer.pve import ChargeMove, FastMove, compute_pve_score


def test_invalid_dodge_factor_raises() -> None:
    fast = FastMove("Quick", power=10, energy_gain=10, duration=1.0)
    charge = ChargeMove("Heavy", power=100, energy_cost=50, duration=2.0)
    with pytest.raises(ValueError):
        compute_pve_score(
            200.0,
            180.0,
            150,
            fast,
            [charge],
            target_defense=180.0,
            incoming_dps=30.0,
            dodge_factor=1.0,
        )
    with pytest.raises(ValueError):
        compute_pve_score(
            200.0,
            180.0,
            150,
            fast,
            [charge],
            target_defense=180.0,
            incoming_dps=30.0,
            dodge_factor=-0.1,
        )


def test_availability_penalty_clamped_and_reflected_in_modifiers() -> None:
    fast = FastMove("Quick", power=10, energy_gain=10, duration=1.0)
    charge = ChargeMove("Heavy", power=100, energy_cost=50, duration=2.0)
    result = compute_pve_score(
        200.0,
        180.0,
        150,
        fast,
        [charge],
        target_defense=180.0,
        incoming_dps=30.0,
        availability_penalty=1.5,
    )
    mods = result["modifiers"]
    # clamped to 0.99 -> factor = 0.01
    assert 0.0 < mods.get("availability_penalty", 1.0) < 1.0

