"""Scoring helpers shared between the raid scoreboard scripts."""

from __future__ import annotations


def iv_bonus(a: int, d: int, s: int) -> float:
    """Light-touch IV bonus for raids; Attack weighted more."""
    return round((a / 15) * 2.0 + (d / 15) * 0.5 + (s / 15) * 0.5, 2)  # max ~3.0


def raid_score(
    base: float,
    ivb: float = 0.0,
    *,
    lucky: bool = False,
    needs_tm: bool = False,
    mega_bonus_now: bool = False,
    mega_bonus_soon: bool = False,
) -> float:
    """Aggregate score with bounded range [1, 100]."""
    sc = base + ivb
    if lucky:
        sc += 3
    if needs_tm:
        sc -= 2
    if mega_bonus_now:
        sc += 4
    elif mega_bonus_soon:
        sc += 1
    return max(1, min(100, round(sc, 1)))


__all__ = ["iv_bonus", "raid_score"]
