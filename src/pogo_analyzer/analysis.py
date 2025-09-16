"""High level Pokémon analysis functions."""
from __future__ import annotations

from typing import Any, Dict, Tuple

from . import data_loader, calculations, events
from .models import PokemonSpecies, Move


def analyze_pokemon(
    name: str,
    form: str,
    ivs: Tuple[int, int, int],
    level: float,
    *,
    shadow: bool = False,
    purified: bool = False,
    best_buddy: bool = False,
) -> Dict:
    stats_map = data_loader.load_pokemon_stats()
    moves_map = data_loader.load_pokemon_moves()
    move_data = data_loader.load_moves()
    event_modifiers = events.get_active_modifiers()

    species: PokemonSpecies = stats_map[name][form]
    stats = calculations.compute_stats(
        species, ivs, level, shadow=shadow, purified=purified, buddy=best_buddy
    )
    cp = calculations.calc_cp(stats, stats["level"])

    moves = moves_map[name][form]
    selected_moves = {
        "fast": list(moves["fast"]),
        "charged": list(moves["charged"]),
    }

    event_move_override = (
        event_modifiers.get("moves", {})
        .get(name, {})
        .get(form)
    )
    if event_move_override:
        if event_move_override.get("fast"):
            selected_moves["fast"] = event_move_override["fast"]
        if event_move_override.get("charged"):
            selected_moves["charged"] = event_move_override["charged"]

    def resolve_move(candidates: Tuple[str, ...] | list[str], fallback: Tuple[str, ...] | list[str]) -> Move:
        for move_name in candidates:
            move = move_data.get(move_name)
            if move is not None:
                return move
        for move_name in fallback:
            move = move_data.get(move_name)
            if move is not None:
                return move
        raise KeyError(f"No known moves available for {name} ({form})")

    fast_move: Move = resolve_move(selected_moves["fast"], moves["fast"])
    charged_move: Move = resolve_move(selected_moves["charged"], moves["charged"])
    pve_bp = calculations.pve_breakpoints(stats, fast_move, boss_def=200)
    pve_sc = calculations.pve_score(stats, {"fast": fast_move, "charged": charged_move})
    league_caps: Dict[str, int] = dict(data_loader.LEAGUE_CP_CAPS)
    applied_cp_caps: Dict[str, calculations.EventCapModifier] = {}
    for league, override in event_modifiers.get("cp_caps", {}).items():
        value = override.get("value") if isinstance(override, dict) else override
        if value is None:
            continue
        league_caps[league] = int(value)
        applied_cp_caps[league] = {
            "value": int(value),
            "event": override.get("event") if isinstance(override, dict) else None,
        }

    pvp_rec = calculations.pvp_recommendation(species, ivs, league_caps=league_caps)
    for league, modifier in applied_cp_caps.items():
        if league in pvp_rec:
            pvp_rec[league]["event_modifier"] = modifier

    event_summary: Dict[str, Any] = {
        "active_events": list(event_modifiers.get("active_events", [])),
        "moves": {},
        "cp_caps": applied_cp_caps,
    }
    if event_move_override:
        event_summary["moves"] = {
            name: {
                form: {
                    "fast": list(event_move_override.get("fast", [])),
                    "charged": list(event_move_override.get("charged", [])),
                    "event": event_move_override.get("event"),
                }
            }
        }
    return {
        "name": name,
        "form": form,
        "level": stats["level"],
        "cp": cp,
        "pve": {
            "breakpoints": pve_bp,
            "score": pve_sc,
            "moveset": {"fast": fast_move.name, "charged": charged_move.name},
        },
        "pvp": pvp_rec,
        "event_modifiers": event_summary,
    }
