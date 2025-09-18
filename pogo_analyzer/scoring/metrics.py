"""Helpers for converting raid evaluation heuristics into numeric scores."""

from __future__ import annotations

from typing import Final

SCORE_MIN: Final = 1
SCORE_MAX: Final = 100


def calculate_iv_bonus(attack_iv: int, defence_iv: int, stamina_iv: int) -> float:
    """Return the additive IV modifier used by :func:`calculate_raid_score`."""

    # Weight Attack twice as heavily as Defence/Stamina to reflect raid damage
    # breakpoints, then round to mimic the original spreadsheet heuristics.
    return round(
        (attack_iv / 15) * 2.0 + (defence_iv / 15) * 0.5 + (stamina_iv / 15) * 0.5,
        2,
    )


def iv_bonus(attack_iv: int, defence_iv: int, stamina_iv: int) -> float:
    """Backward-compatible alias for :func:`calculate_iv_bonus`."""

    return calculate_iv_bonus(attack_iv, defence_iv, stamina_iv)


def calculate_raid_score(
    base_score: float,
    iv_bonus_value: float = 0.0,
    *,
    lucky: bool = False,
    needs_tm: bool = False,
    mega_bonus_now: bool = False,
    mega_bonus_soon: bool = False,
) -> float:
    """Combine baseline species strength and modifiers into a raid score."""

    score = base_score + iv_bonus_value
    if lucky:
        score += 3
    if needs_tm:
        score -= 2
    if mega_bonus_now:
        score += 4
    elif mega_bonus_soon:
        score += 1
    return max(SCORE_MIN, min(SCORE_MAX, round(score, 1)))


def raid_score(
    base: float,
    ivb: float = 0.0,
    *,
    lucky: bool = False,
    needs_tm: bool = False,
    mega_bonus_now: bool = False,
    mega_bonus_soon: bool = False,
) -> float:
    """Backward-compatible alias for :func:`calculate_raid_score`."""

    return calculate_raid_score(
        base,
        ivb,
        lucky=lucky,
        needs_tm=needs_tm,
        mega_bonus_now=mega_bonus_now,
        mega_bonus_soon=mega_bonus_soon,
    )


__all__ = [
    "SCORE_MAX",
    "SCORE_MIN",
    "calculate_iv_bonus",
    "calculate_raid_score",
    "iv_bonus",
    "raid_score",
]
