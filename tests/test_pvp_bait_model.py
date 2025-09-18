"""Tests for PvP bait model integration in compute_pvp_score."""

from __future__ import annotations

import math

import pytest

from pogo_analyzer.pvp import (
    DEFAULT_LEAGUE_CONFIGS,
    LeagueConfig,
    PvpChargeMove,
    PvpFastMove,
    compute_pvp_score,
)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def test_bait_model_overrides_probability_across_shield_scenarios() -> None:
    fast = PvpFastMove(name="Snarl", damage=5, energy_gain=13, turns=4)  # EPT=6.5, DPT=2.5 per second
    # Two charges to enable pair calculation
    high = PvpChargeMove(name="Hyper Beam", damage=150, energy_cost=80)
    low = PvpChargeMove(name="Crunch", damage=70, energy_cost=45)

    # Override league bait model
    cfg: LeagueConfig = DEFAULT_LEAGUE_CONFIGS["great"]
    bait_model = {"a": 0.4, "b": -0.1, "c": 0.35, "d": 0.0}
    league_configs = dict(DEFAULT_LEAGUE_CONFIGS)
    league_configs["great"] = LeagueConfig(
        cp_cap=cfg.cp_cap,
        stat_product_reference=cfg.stat_product_reference,
        move_pressure_reference=cfg.move_pressure_reference,
        bait_probability=cfg.bait_probability,
        shield_weights=(0.2, 0.5, 0.3),
        bait_model=bait_model,
        cmp_threshold=cfg.cmp_threshold,
        cmp_eta=cfg.cmp_eta,
        coverage_theta=cfg.coverage_theta,
        anti_meta_mu=cfg.anti_meta_mu,
    )

    result = compute_pvp_score(
        attack=150.0,
        defense=150.0,
        stamina=160,
        fast_move=fast,
        charge_moves=[high, low],
        league="great",
        shield_weights=[0.2, 0.5, 0.3],
        league_configs=league_configs,
    )

    assert "shield_breakdown" in result
    breakdown = result["shield_breakdown"]

    # Expected bait probabilities based on EPT/DPT and shields
    turns_seconds = fast.turns * 0.5
    ept = fast.energy_gain / turns_seconds
    dpt = fast.damage / turns_seconds
    for entry in breakdown:
        shields = int(entry["shield_count"])  # 0,1,2
        expected = _sigmoid(bait_model["a"] * ept + bait_model["b"] * dpt + bait_model["c"] * shields + bait_model["d"])
        assert entry["bait_probability"] == pytest.approx(expected, rel=1e-6)

