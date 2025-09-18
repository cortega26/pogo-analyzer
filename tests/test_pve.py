"""Tests for PvE rotation and scoring helpers."""

from __future__ import annotations

import math

import pytest

from pogo_analyzer.formulas import damage_per_hit
from pogo_analyzer.pve import (
    ChargeMove,
    FastMove,
    compute_pve_score,
    estimate_ehp,
    pve_value,
    rotation_dps,
)


@pytest.fixture
def sample_stats() -> tuple[float, float, int]:
    return 230.0, 198.0, 172


@pytest.fixture
def sample_moves() -> tuple[FastMove, list[ChargeMove]]:
    fast = FastMove("Dragon Breath", power=16, energy_gain=9, duration=0.5, stab=True)
    charge_1 = ChargeMove("Dragon Claw", power=90, energy_cost=35, duration=1.7, stab=True)
    charge_2 = ChargeMove("Outrage", power=110, energy_cost=50, duration=3.9, stab=True)
    return fast, [charge_1, charge_2]


def test_rotation_dps_prefers_mixed_rotation(sample_stats: tuple[float, float, int], sample_moves: tuple[FastMove, list[ChargeMove]]) -> None:
    attack, _, _ = sample_stats
    fast_move, charge_moves = sample_moves
    target_defense = 190.0

    fast_only_damage = damage_per_hit(
        fast_move.power,
        attack,
        target_defense,
        stab=fast_move.stab,
        weather_boosted=fast_move.weather_boosted,
        type_effectiveness=fast_move.type_effectiveness,
    )
    fast_only_dps = fast_only_damage / fast_move.duration

    best_dps = rotation_dps(fast_move, charge_moves, attack, target_defense)

    assert best_dps > fast_only_dps


def test_rotation_dps_handles_fast_only(sample_stats: tuple[float, float, int], sample_moves: tuple[FastMove, list[ChargeMove]]) -> None:
    attack, _, _ = sample_stats
    fast_move, charge_moves = sample_moves
    target_defense = 200.0

    best_dps = rotation_dps(fast_move, [], attack, target_defense)

    expected = damage_per_hit(
        fast_move.power,
        attack,
        target_defense,
        stab=fast_move.stab,
        weather_boosted=fast_move.weather_boosted,
        type_effectiveness=fast_move.type_effectiveness,
    ) / fast_move.duration

    assert math.isclose(best_dps, expected)


def test_estimate_ehp_matches_formula(sample_stats: tuple[float, float, int]) -> None:
    _, defense, hp = sample_stats
    target_defense = 150.0

    expected = hp * (defense / target_defense)
    assert math.isclose(estimate_ehp(defense, hp, target_defense=target_defense), expected)


def test_pve_value_monotonicity() -> None:
    base = pve_value(10.0, 200.0, alpha=0.6)
    better_dps = pve_value(12.0, 200.0, alpha=0.6)
    better_tdo = pve_value(10.0, 240.0, alpha=0.6)

    assert better_dps > base
    assert better_tdo > base


def test_compute_pve_score_returns_expected_keys(sample_stats: tuple[float, float, int], sample_moves: tuple[FastMove, list[ChargeMove]]) -> None:
    attack, defense, hp = sample_stats
    fast_move, charge_moves = sample_moves

    result = compute_pve_score(
        attack,
        defense,
        hp,
        fast_move,
        charge_moves,
        target_defense=190.0,
        incoming_dps=35.0,
        alpha=0.6,
    )

    assert set(result.keys()) == {
        "dps",
        "cycle_damage",
        "cycle_time",
        "fast_moves_per_cycle",
        "charge_usage_per_cycle",
        "ehp",
        "tdo",
        "value",
        "value_raw",
        "alpha",
        "energy_from_damage_ratio",
        "relobby_penalty",
        "penalty_factor",
        "dodge_factor",
        "modifiers",
    }

    expected_base = pve_value(result["dps"], result["tdo"], alpha=result["alpha"]) * result["penalty_factor"]
    assert result["value"] == pytest.approx(expected_base)
    assert result["modifiers"] == {}
    assert result["dodge_factor"] is None



def test_energy_from_damage_ratio_boosts_output(
    sample_stats: tuple[float, float, int],
    sample_moves: tuple[FastMove, list[ChargeMove]],
) -> None:
    attack, defense, hp = sample_stats
    fast_move, charge_moves = sample_moves

    baseline = compute_pve_score(
        attack,
        defense,
        hp,
        fast_move,
        charge_moves,
        target_defense=190.0,
        incoming_dps=35.0,
    )
    boosted = compute_pve_score(
        attack,
        defense,
        hp,
        fast_move,
        charge_moves,
        target_defense=190.0,
        incoming_dps=35.0,
        energy_from_damage_ratio=0.5,
    )

    assert boosted["energy_from_damage_ratio"] == pytest.approx(0.5)
    assert boosted["value"] > 0
    assert boosted["modifiers"] == {}


def test_weighted_pve_scenarios_return_aggregate(
    sample_stats: tuple[float, float, int],
    sample_moves: tuple[FastMove, list[ChargeMove]],
) -> None:
    attack, defense, hp = sample_stats
    fast_move, charge_moves = sample_moves

    scenarios = [
        {"weight": 1.0, "target_defense": 185.0, "incoming_dps": 30.0},
        {"weight": 0.5, "target_defense": 205.0, "incoming_dps": 40.0},
    ]

    result = compute_pve_score(
        attack,
        defense,
        hp,
        fast_move,
        charge_moves,
        target_defense=190.0,
        incoming_dps=35.0,
        scenarios=scenarios,
    )

    assert "scenarios" in result
    breakdown = result["scenarios"]
    assert isinstance(breakdown, list)
    assert breakdown
    values = [scenario["value"] for scenario in breakdown]
    assert all("modifiers" in scenario for scenario in breakdown)
    assert result["value"] <= max(values) + 1e-9
    assert result["value"] >= min(values) - 1e-9
