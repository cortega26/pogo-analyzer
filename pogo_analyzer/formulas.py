"""Core formulas for inferring Pokémon GO levels, stats, and damage."""

from __future__ import annotations

import math
from typing import Iterable

from .cpm_table import get_cpm

_EPSILON = 1e-9


def _pre_cpm_stats(
    base_attack: int,
    base_defense: int,
    base_stamina: int,
    iv_attack: int,
    iv_defense: int,
    iv_stamina: int,
    *,
    is_shadow: bool,
) -> tuple[float, float, float]:
    """Return the pre-CPM stats ``(A0, D0, S0)`` for the supplied Pokémon."""

    shadow_attack_multiplier = 1.2 if is_shadow else 1.0
    shadow_defense_multiplier = 0.83 if is_shadow else 1.0

    attack = (base_attack + iv_attack) * shadow_attack_multiplier
    defense = (base_defense + iv_defense) * shadow_defense_multiplier
    stamina = base_stamina + iv_stamina
    return attack, defense, stamina


def _candidate_levels() -> Iterable[float]:
    """Yield all valid Pokémon levels between 1 and 50 inclusive in 0.5 steps."""

    return (level / 2 for level in range(2, 101))


def infer_level_from_cp(
    base_attack: int,
    base_defense: int,
    base_stamina: int,
    iv_attack: int,
    iv_defense: int,
    iv_stamina: int,
    cp: int,
    *,
    is_shadow: bool = False,
    is_best_buddy: bool = False,
    observed_hp: int | None = None,
) -> tuple[float, float]:
    """Infer the Pokémon's level from its Combat Power (CP).

    The function iterates the discrete level ladder (1.0–50.0 in 0.5
    increments), applies the CP formula from
    :mod:`pokemon_value_formulas.md`, and identifies the unique level whose
    rounded CP matches the observed value. Best Buddy status is modelled as
    the spec dictates by applying the CPM of ``level + 1``. Shadow attack and
    defense modifiers are applied to the base+IV stats prior to the CPM.

    Args:
        base_attack: Species base attack.
        base_defense: Species base defense.
        base_stamina: Species base stamina.
        iv_attack: Individual value (0–15) for attack.
        iv_defense: Individual value (0–15) for defense.
        iv_stamina: Individual value (0–15) for stamina.
        cp: Observed Combat Power for the Pokémon.
        is_shadow: Whether the Pokémon is shadow (1.2× attack, 0.83× defense).
        is_best_buddy: Whether the Best Buddy +1 level CPM bonus applies.
        observed_hp: Optional observed HP used to disambiguate rare CP
            collisions across levels.

    Returns:
        A pair ``(level, effective_cpm)`` where ``level`` is the inferred
        underlying level (without the Best Buddy offset) and ``effective_cpm``
        is the CPM actually applied to stats (including Best Buddy effects).

    Raises:
        ValueError: If the CP cannot be produced with the provided inputs or
            if multiple levels map to the same CP without sufficient HP
            information to disambiguate the result.
    """

    if cp < 0:
        raise ValueError("CP must be non-negative.")
    if observed_hp is not None and observed_hp < 0:
        raise ValueError("Observed HP must be non-negative when provided.")

    A0, D0, S0 = _pre_cpm_stats(
        base_attack,
        base_defense,
        base_stamina,
        iv_attack,
        iv_defense,
        iv_stamina,
        is_shadow=is_shadow,
    )
    best_buddy_offset = 1.0 if is_best_buddy else 0.0
    candidates: list[tuple[float, float, int]] = []

    for level in _candidate_levels():
        cpm = get_cpm(level + best_buddy_offset)
        cp_estimate = math.floor(
            (A0 * math.sqrt(D0) * math.sqrt(S0) * cpm**2 / 10) + _EPSILON
        )
        if cp_estimate == cp:
            hp_estimate = math.floor(S0 * cpm + _EPSILON)
            candidates.append((level, cpm, hp_estimate))

    if not candidates:
        raise ValueError("Observed CP is inconsistent with the provided inputs.")

    if len(candidates) == 1:
        level, cpm, _ = candidates[0]
        return level, cpm

    if observed_hp is not None:
        filtered = [candidate for candidate in candidates if candidate[2] == observed_hp]
        if len(filtered) == 1:
            level, cpm, _ = filtered[0]
            return level, cpm
        if not filtered:
            raise ValueError(
                "Observed HP does not match any level that yields the observed CP."
            )
        candidates = filtered

    raise ValueError(
        "Observed CP corresponds to multiple levels; provide observed HP to disambiguate."
    )


def effective_stats(
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
) -> tuple[float, float, int]:
    """Compute the post-CPM attack, defense, and HP values for a Pokémon.

    Args:
        base_attack: Species base attack.
        base_defense: Species base defense.
        base_stamina: Species base stamina.
        iv_attack: Individual value for attack.
        iv_defense: Individual value for defense.
        iv_stamina: Individual value for stamina.
        level: The Pokémon's level (without Best Buddy offset).
        is_shadow: Whether the Pokémon is shadow.
        is_best_buddy: Whether the Best Buddy CPM bonus is active.

    Returns:
        A tuple ``(attack, defense, hp)`` where ``attack`` and ``defense`` are
        floating point values representing the scaled stats and ``hp`` is the
        floored stamina value as displayed in-game.
    """

    A0, D0, S0 = _pre_cpm_stats(
        base_attack,
        base_defense,
        base_stamina,
        iv_attack,
        iv_defense,
        iv_stamina,
        is_shadow=is_shadow,
    )
    cpm = get_cpm(level + (1.0 if is_best_buddy else 0.0))

    attack = A0 * cpm
    defense = D0 * cpm
    hp = math.floor(S0 * cpm + _EPSILON)
    return attack, defense, hp


def damage_per_hit(
    move_power: float,
    attacker_attack: float,
    defender_defense: float,
    *,
    stab: bool = False,
    weather_boosted: bool = False,
    type_effectiveness: float = 1.0,
) -> int:
    """Evaluate the PvE per-hit damage formula from the specification.

    Args:
        move_power: The move's listed power.
        attacker_attack: Effective attack of the attacker.
        defender_defense: Effective defense of the defender. Must be positive.
        stab: ``True`` when Same-Type-Attack-Bonus applies (1.2× multiplier).
        weather_boosted: ``True`` if weather boost applies (1.2× multiplier).
        type_effectiveness: Combined type effectiveness multiplier
            (e.g. 1.6 for super-effective, 0.625 for resisted).

    Returns:
        The integer damage dealt by one execution of the move.

    Raises:
        ValueError: If ``defender_defense`` or ``type_effectiveness`` are not
            positive or if ``move_power`` is negative.
    """

    if defender_defense <= 0:
        raise ValueError("defender_defense must be positive.")
    if type_effectiveness <= 0:
        raise ValueError("type_effectiveness must be positive.")
    if move_power < 0:
        raise ValueError("move_power cannot be negative.")

    multiplier = (1.2 if stab else 1.0) * (1.2 if weather_boosted else 1.0)
    multiplier *= type_effectiveness

    raw_damage = 0.5 * move_power * (attacker_attack / defender_defense) * multiplier
    return math.floor(raw_damage + _EPSILON) + 1


__all__ = ["infer_level_from_cp", "effective_stats", "damage_per_hit"]
