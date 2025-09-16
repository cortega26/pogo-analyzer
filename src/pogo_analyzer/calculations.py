"""Core stat and CP calculations."""
from __future__ import annotations

from math import floor, sqrt
from typing import Dict, NotRequired, Optional, Tuple, TypedDict

from .models import PokemonSpecies, Move
from . import data_loader


class SecondMoveCost(TypedDict):
    stardust: int
    candy: int


class StatProductResult(TypedDict):
    level: float
    cp: int
    stat_product: float
    requires_xl: bool
    second_move_cost: SecondMoveCost


class EventCapModifier(TypedDict):
    value: int
    event: str | None


class PvPLeagueRecommendation(StatProductResult):
    cap: int
    event_modifier: NotRequired[EventCapModifier]


def compute_stats(
    species: PokemonSpecies,
    ivs: Tuple[int, int, int],
    level: float,
    shadow: bool = False,
    purified: bool = False,
    buddy: bool = False,
) -> Dict[str, float]:
    """Return effective attack, defense, stamina, and level."""
    atk = float(species.base_attack + ivs[0])
    defense = float(species.base_defense + ivs[1])
    stamina = float(species.base_stamina + ivs[2])
    if shadow:
        atk *= data_loader.SHADOW_ATTACK_MULT
        defense *= data_loader.SHADOW_DEFENSE_MULT
    if purified:
        atk += data_loader.PURIFIED_ATTACK_BONUS
        defense *= data_loader.PURIFIED_DEFENSE_MULT
    eff_level = level + (data_loader.BEST_BUDDY_LEVEL_BONUS if buddy else 0)
    return {"attack": atk, "defense": defense, "stamina": stamina, "level": eff_level}


def calc_cp(stats: Dict[str, float], level: float) -> int:
    multipliers = data_loader.load_cp_multipliers()
    m = multipliers.get(level)
    if m is None:
        raise ValueError(f"Unknown CP multiplier for level {level}")
    cp = floor(
        (stats["attack"] * sqrt(stats["defense"]) * sqrt(stats["stamina"]) * m * m)
        / 10
    )
    return max(10, int(cp))


def pve_breakpoints(stats: Dict[str, float], move: Move, boss_def: float) -> Tuple[Tuple[float, int], ...]:
    """Return levels where fast move damage increases against a boss."""
    mults = data_loader.load_cp_multipliers()
    out = []
    prev = None
    for level in sorted(mults):
        if level < 1 or level > 50:
            continue
        atk = stats["attack"] * mults[level]
        dmg = floor(0.5 * move.power * atk / boss_def) + 1
        if prev is None or dmg > prev:
            out.append((level, dmg))
            prev = dmg
    return tuple(out)


def pve_score(stats: Dict[str, float], moveset: Dict[str, Move]) -> float:
    fast = moveset["fast"]
    charged = moveset["charged"]
    dps = fast.power / max(fast.duration, 1) + charged.power / max(charged.duration, 1)
    return stats["attack"] * dps


def maximize_stat_product(
    species: PokemonSpecies, ivs: Tuple[int, int, int], league_cap: int
) -> StatProductResult:
    mults = data_loader.load_cp_multipliers()
    best: StatProductResult = {
        "level": 1.0,
        "cp": 10,
        "stat_product": 0.0,
        "requires_xl": False,
        "second_move_cost": {"stardust": 50000, "candy": 50},
    }
    for level in sorted(mults):
        if level > 55:
            continue
        stats = compute_stats(species, ivs, level)
        cp = calc_cp(stats, level)
        if cp > league_cap:
            break
        product = stats["attack"] * stats["defense"] * stats["stamina"]
        if product > best["stat_product"]:
            best = {
                "level": level,
                "cp": cp,
                "stat_product": product,
                "requires_xl": level > 40,
                "second_move_cost": {"stardust": 50000, "candy": 50},
            }
    return best


def pvp_recommendation(
    species: PokemonSpecies,
    ivs: Tuple[int, int, int],
    *,
    league_caps: Optional[Dict[str, int]] = None,
) -> Dict[str, PvPLeagueRecommendation]:
    caps = league_caps or data_loader.LEAGUE_CP_CAPS
    rec: Dict[str, PvPLeagueRecommendation] = {}
    for league, cap in caps.items():
        base = maximize_stat_product(species, ivs, cap)
        league_rec: PvPLeagueRecommendation = {
            "level": base["level"],
            "cp": base["cp"],
            "stat_product": base["stat_product"],
            "requires_xl": base["requires_xl"],
            "second_move_cost": base["second_move_cost"],
            "cap": cap,
        }
        rec[league] = league_rec
    return rec
