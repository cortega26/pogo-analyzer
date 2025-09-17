"""Tests for the stat and damage formulas."""

from __future__ import annotations

import math

import pytest

from pogo_analyzer.cpm_table import get_cpm
from pogo_analyzer.formulas import damage_per_hit, effective_stats, infer_level_from_cp


def _compute_cp(
    base_attack: int,
    base_defense: int,
    base_stamina: int,
    iv_attack: int,
    iv_defense: int,
    iv_stamina: int,
    level: float,
    *,
    is_shadow: bool = False,
    is_best_buddy: bool = False,
) -> int:
    """Reference implementation of the CP formula from the specification."""

    attack = (base_attack + iv_attack) * (1.2 if is_shadow else 1.0)
    defense = (base_defense + iv_defense) * (0.83 if is_shadow else 1.0)
    stamina = base_stamina + iv_stamina
    cpm = get_cpm(level + (1 if is_best_buddy else 0))
    return math.floor(attack * math.sqrt(defense) * math.sqrt(stamina) * cpm**2 / 10)


def test_infer_level_basic_case() -> None:
    cp = _compute_cp(190, 190, 190, 12, 15, 10, 31.0)
    level, cpm = infer_level_from_cp(190, 190, 190, 12, 15, 10, cp)
    assert level == 31.0
    assert cpm == pytest.approx(get_cpm(31.0))


def test_infer_level_shadow_best_buddy() -> None:
    cp = _compute_cp(250, 180, 180, 15, 13, 14, 36.5, is_shadow=True, is_best_buddy=True)
    level, cpm = infer_level_from_cp(
        250,
        180,
        180,
        15,
        13,
        14,
        cp,
        is_shadow=True,
        is_best_buddy=True,
    )
    assert level == 36.5
    assert cpm == pytest.approx(get_cpm(37.5))


def test_infer_level_requires_hp_disambiguation() -> None:
    cp = _compute_cp(10, 10, 10, 0, 0, 0, 1.0)
    with pytest.raises(ValueError):
        infer_level_from_cp(10, 10, 10, 0, 0, 0, cp)

    level, _ = infer_level_from_cp(10, 10, 10, 0, 0, 0, cp, observed_hp=0)
    assert level == 1.0


def test_effective_stats_matches_spec() -> None:
    cp = _compute_cp(180, 200, 190, 15, 12, 13, 35.5, is_shadow=True)
    level, cpm = infer_level_from_cp(180, 200, 190, 15, 12, 13, cp, is_shadow=True)
    attack, defense, hp = effective_stats(180, 200, 190, 15, 12, 13, level, is_shadow=True)
    # Manual calculations from spec definitions.
    attack0 = (180 + 15) * 1.2
    defense0 = (200 + 12) * 0.83
    stamina0 = 190 + 13
    assert attack == pytest.approx(attack0 * cpm)
    assert defense == pytest.approx(defense0 * cpm)
    assert hp == math.floor(stamina0 * cpm)


def test_damage_per_hit_full_multipliers() -> None:
    attack, _, _ = effective_stats(198, 189, 190, 15, 15, 15, 40.0)
    damage = damage_per_hit(100, attack, 200.0, stab=True, weather_boosted=True, type_effectiveness=1.6)
    expected = math.floor(0.5 * 100 * (attack / 200.0) * (1.2 * 1.2 * 1.6)) + 1
    assert damage == expected


def test_damage_per_hit_validation() -> None:
    with pytest.raises(ValueError):
        damage_per_hit(50, 200.0, 0.0)

    with pytest.raises(ValueError):
        damage_per_hit(50, 200.0, 100.0, type_effectiveness=0.0)

    with pytest.raises(ValueError):
        damage_per_hit(-1, 200.0, 100.0)
