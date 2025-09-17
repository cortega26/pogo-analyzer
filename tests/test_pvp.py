"""Tests for PvP scoring helpers."""

from __future__ import annotations

import pytest

from pogo_analyzer.pvp import (
    BUFF_WEIGHT,
    DEFAULT_BETA,
    DEFAULT_LEAGUE_CONFIGS,
    FAST_MOVE_ENERGY_WEIGHT,
    LeagueConfig,
    PvpChargeMove,
    PvpFastMove,
    charge_move_pressure,
    compute_pvp_score,
    fast_move_pressure,
    move_pressure,
    normalise,
    pair_charge_pressure,
    stat_product,
)


def test_stat_product_multiplies_components() -> None:
    assert stat_product(100.0, 120.0, 150) == pytest.approx(100.0 * 120.0 * 150)


def test_fast_and_charge_move_pressure_follow_spec() -> None:
    fast = PvpFastMove(name="Shadow Claw", damage=3, energy_gain=9, turns=3)
    charge_heavy = PvpChargeMove(name="Shadow Ball", damage=110, energy_cost=55)
    charge_bait = PvpChargeMove(name="Shadow Punch", damage=40, energy_cost=35)

    fast_expected = (3 / (3 * 0.5)) + (FAST_MOVE_ENERGY_WEIGHT * (9 / (3 * 0.5)))
    assert fast_move_pressure(fast) == pytest.approx(fast_expected)

    heavy_expected = charge_heavy.effective_reliability * (110 + 0.0)
    bait_expected = charge_bait.effective_reliability * (40 + 0.0)

    assert charge_move_pressure(charge_heavy) == pytest.approx(heavy_expected)
    assert charge_move_pressure(charge_bait) == pytest.approx(bait_expected)

    bait_probability = 0.6
    pair_expected = (bait_probability * heavy_expected) + ((1 - bait_probability) * bait_expected)
    assert pair_charge_pressure(charge_heavy, charge_bait, bait_probability=bait_probability) == pytest.approx(pair_expected)


def test_move_pressure_uses_best_of_single_and_pair() -> None:
    fast = PvpFastMove(name="Counter", damage=4, energy_gain=8, turns=2)
    nuke = PvpChargeMove(name="Focus Blast", damage=150, energy_cost=75)
    bait = PvpChargeMove(name="Rock Slide", damage=70, energy_cost=40)

    fast_component = fast_move_pressure(fast)
    single_best = max(
        charge_move_pressure(nuke),
        charge_move_pressure(bait),
    )
    pair_component = pair_charge_pressure(nuke, bait, bait_probability=0.5)
    expected = fast_component + max(single_best, pair_component)

    assert move_pressure(fast, [nuke, bait], bait_probability=0.5) == pytest.approx(expected)


def test_compute_pvp_score_applies_config_defaults() -> None:
    fast = PvpFastMove(name="Dragon Breath", damage=4, energy_gain=3, turns=1)
    nuke = PvpChargeMove(name="Dragon Claw", damage=50, energy_cost=35)
    bait = PvpChargeMove(name="Outrage", damage=110, energy_cost=60)

    league_config: LeagueConfig = DEFAULT_LEAGUE_CONFIGS["great"]
    stat_prod = stat_product(150.0, 160.0, 180)
    stat_norm = normalise(stat_prod, league_config.stat_product_reference)
    move_press = move_pressure(
        fast,
        [nuke, bait],
        bait_probability=league_config.bait_probability,
    )
    move_norm = normalise(move_press, league_config.move_pressure_reference)
    expected_score = (stat_norm ** DEFAULT_BETA) * (move_norm ** (1 - DEFAULT_BETA))

    result = compute_pvp_score(
        150.0,
        160.0,
        180,
        fast,
        [nuke, bait],
        league="great",
    )

    assert result["stat_product"] == pytest.approx(stat_prod)
    assert result["stat_product_normalised"] == pytest.approx(stat_norm)
    assert result["move_pressure"] == pytest.approx(move_press)
    assert result["move_pressure_normalised"] == pytest.approx(move_norm)
    assert result["score"] == pytest.approx(expected_score)


def test_compute_pvp_score_custom_overrides() -> None:
    fast = PvpFastMove(name="Vine Whip", damage=3, energy_gain=8, turns=2)
    nuke = PvpChargeMove(name="Frenzy Plant", damage=100, energy_cost=45, has_buff=True)
    bait = PvpChargeMove(name="Sludge Bomb", damage=80, energy_cost=50)

    result = compute_pvp_score(
        120.0,
        140.0,
        160,
        fast,
        [nuke, bait],
        league="ultra",
        beta=0.6,
        stat_product_reference=2_000_000,
        move_pressure_reference=60.0,
        bait_probability=0.3,
        energy_weight=0.4,
        buff_weight=BUFF_WEIGHT,
    )

    assert result["stat_product_normalised"] > 1.0
    assert 0 < result["move_pressure_normalised"]
    assert 0 < result["score"]


def test_invalid_inputs_raise_errors() -> None:
    fast = PvpFastMove(name="Mud Shot", damage=3, energy_gain=9, turns=1)
    charge = PvpChargeMove(name="Earthquake", damage=120, energy_cost=65)

    with pytest.raises(ValueError):
        stat_product(0.0, 120.0, 160)

    with pytest.raises(ValueError):
        normalise(100.0, 0.0)

    with pytest.raises(ValueError):
        fast_move_pressure(fast, energy_weight=-0.1)

    with pytest.raises(ValueError):
        charge_move_pressure(charge, buff_weight=-1.0)

    with pytest.raises(ValueError):
        pair_charge_pressure(charge, charge, bait_probability=1.5)

    with pytest.raises(ValueError):
        move_pressure(fast, [], bait_probability=0.5)

    with pytest.raises(ValueError):
        compute_pvp_score(
            -10.0,
            120.0,
            150,
            fast,
            [charge],
        )

    with pytest.raises(KeyError):
        compute_pvp_score(
            120.0,
            120.0,
            150,
            fast,
            [charge],
            league="mythic",
        )

    with pytest.raises(ValueError):
        compute_pvp_score(
            120.0,
            120.0,
            150,
            fast,
            [charge],
            beta=1.2,
        )
