"""Helpers for converting raid evaluation heuristics into numeric scores.

The helpers are intentionally light-weight so they can be reused by
``raid_scoreboard_generator`` and any third-party automation without pulling
in heavy dependencies.
"""

from __future__ import annotations


def iv_bonus(a: int, d: int, s: int) -> float:
    """Return the additive IV modifier used by :func:`raid_score`.

    Parameters
    ----------
    a, d, s:
        Attack, Defence, and Stamina IV values (0–15). Attack contributes the
        majority of the bonus because raid damage scales with Attack.

    Returns
    -------
    float
        The rounded IV contribution, capped at roughly ``3.0`` for perfect IVs.
    """

    # Weight Attack twice as heavily as Defence/Stamina to reflect raid damage
    # breakpoints, then round to mimic the original spreadsheet heuristics.
    return round((a / 15) * 2.0 + (d / 15) * 0.5 + (s / 15) * 0.5, 2)


def raid_score(
    base: float,
    ivb: float = 0.0,
    *,
    lucky: bool = False,
    needs_tm: bool = False,
    mega_bonus_now: bool = False,
    mega_bonus_soon: bool = False,
) -> float:
    """Combine baseline species strength and modifiers into a raid score.

    Parameters
    ----------
    base:
        Baseline score for the Pokémon's best raid role. Values typically range
        from the low 50s (poor raiders) to mid 90s (top-tier megas/shadows).
    ivb:
        Output from :func:`iv_bonus`. Defaults to ``0.0`` when IVs are
        unavailable or intentionally ignored.
    lucky:
        Adds ``+3`` when the Pokémon is lucky and therefore cheaper to build.
    needs_tm:
        Subtracts ``2`` when a Community Day or Elite TM move is mandatory.
    mega_bonus_now:
        Adds ``+4`` when the Pokémon currently has a relevant mega evolution
        unlocked.
    mega_bonus_soon:
        Adds ``+1`` when a relevant mega evolution has been announced but is
        not yet available.

    Returns
    -------
    float
        Final raid score rounded to one decimal place and clamped to ``[1, 100]``.
    """

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
