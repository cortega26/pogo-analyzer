"""Regression tests for level inference edge conditions."""

from __future__ import annotations

import math

import pytest

from pogo_analyzer.cpm_table import get_cpm
from pogo_analyzer.formulas import infer_level_from_cp


def _cp_and_hp(
    base_attack: int,
    base_defense: int,
    base_stamina: int,
    iv_attack: int,
    iv_defense: int,
    iv_stamina: int,
    level: float,
) -> tuple[int, int]:
    """Return the (CP, HP) pair for a Pokémon at a specific level."""

    cpm = get_cpm(level)
    attack = base_attack + iv_attack
    defense = base_defense + iv_defense
    stamina = base_stamina + iv_stamina
    cp = math.floor(attack * math.sqrt(defense) * math.sqrt(stamina) * cpm**2 / 10)
    hp = math.floor(stamina * cpm)
    return cp, hp


def test_infer_level_negative_cp_raises() -> None:
    with pytest.raises(ValueError, match="CP must be non-negative"):
        infer_level_from_cp(200, 200, 200, 10, 10, 10, -1)


def test_infer_level_negative_observed_hp_raises() -> None:
    with pytest.raises(ValueError, match="Observed HP must be non-negative"):
        infer_level_from_cp(180, 180, 180, 12, 12, 12, 1000, observed_hp=-5)


def test_infer_level_requires_hp_to_break_cp_collision() -> None:
    base_attack = base_defense = base_stamina = 30
    iv_attack = iv_defense = iv_stamina = 0
    level_low = 17.5
    level_high = 18.0

    cp, hp_low = _cp_and_hp(
        base_attack,
        base_defense,
        base_stamina,
        iv_attack,
        iv_defense,
        iv_stamina,
        level_low,
    )
    cp_check, hp_high = _cp_and_hp(
        base_attack,
        base_defense,
        base_stamina,
        iv_attack,
        iv_defense,
        iv_stamina,
        level_high,
    )
    assert cp == cp_check  # Sanity check that the collision is real.

    with pytest.raises(ValueError, match="multiple levels"):
        infer_level_from_cp(
            base_attack,
            base_defense,
            base_stamina,
            iv_attack,
            iv_defense,
            iv_stamina,
            cp,
        )

    level, _ = infer_level_from_cp(
        base_attack,
        base_defense,
        base_stamina,
        iv_attack,
        iv_defense,
        iv_stamina,
        cp,
        observed_hp=hp_high,
    )
    assert level == pytest.approx(level_high)

    with pytest.raises(ValueError, match="does not match any level"):
        infer_level_from_cp(
            base_attack,
            base_defense,
            base_stamina,
            iv_attack,
            iv_defense,
            iv_stamina,
            cp,
            observed_hp=hp_high + 5,
        )
