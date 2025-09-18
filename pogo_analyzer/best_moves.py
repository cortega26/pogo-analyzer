from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .pve import FastMove, ChargeMove, compute_pve_score
from .pvp import PvpFastMove, PvpChargeMove, move_pressure


@dataclass(frozen=True)
class BestMoves:
    pve_fast: str
    pve_charge1: str
    pve_charge2: str | None
    pvp_fast: str
    pvp_charge1: str
    pvp_charge2: str | None


def _build_fast_pve(entry: Mapping[str, float]) -> FastMove:
    return FastMove(
        name=entry["name"],
        power=float(entry.get("pve_power", 0.0)),
        energy_gain=float(entry.get("pve_energy_gain", 0.0)),
        duration=float(entry.get("pve_duration_s", 1.0) or 1.0),
    )


def _build_charge_pve(entry: Mapping[str, float]) -> ChargeMove:
    return ChargeMove(
        name=entry["name"],
        power=float(entry.get("pve_power", 0.0)),
        energy_cost=float(abs(entry.get("pve_energy_gain", -50.0) or 50.0)),
        duration=float(entry.get("pve_duration_s", 1.0) or 1.0),
    )


def _build_fast_pvp(entry: Mapping[str, float]) -> PvpFastMove:
    return PvpFastMove(
        name=entry["name"],
        damage=float(entry.get("pvp_damage", 0.0)),
        energy_gain=float(entry.get("pvp_energy_gain", 0.0)),
        turns=int(entry.get("pvp_turns", 1) or 1),
    )


def _build_charge_pvp(entry: Mapping[str, float]) -> PvpChargeMove:
    return PvpChargeMove(
        name=entry["name"],
        damage=float(entry.get("pvp_damage", 0.0)),
        energy_cost=float(abs(entry.get("pvp_energy_gain", -50.0) or 50.0)),
    )


def compute_best_moves(
    species: str,
    *,
    species_types: Sequence[str] | None,
    species_stats: tuple[float, float, int] | None,
    normalized_moves_path: str | Path,
    learnsets_path: str | Path,
) -> BestMoves | None:
    moves_payload = json.loads(Path(normalized_moves_path).read_text(encoding="utf-8"))
    learnsets = json.loads(Path(learnsets_path).read_text(encoding="utf-8"))
    ls = learnsets.get(species) or learnsets.get(species.title()) or learnsets.get(species.lower())
    if not ls:
        return None

    fast_map = {m["name"]: m for m in moves_payload.get("fast", [])}
    charge_map = {m["name"]: m for m in moves_payload.get("charge", [])}
    fast_candidates = [fast_map.get(n) for n in ls.get("fast", []) if n in fast_map]
    charge_candidates = [charge_map.get(n) for n in ls.get("charge", []) if n in charge_map]
    fast_candidates = [m for m in fast_candidates if m]
    charge_candidates = [m for m in charge_candidates if m]
    if not fast_candidates or not charge_candidates:
        return None

    # PvE: evaluate fast x charge1 pairs; pick highest value at default context
    pve_best = (None, None, 0.0)
    atk, dfn, hp = species_stats or (250.0, 200.0, 170)
    for f in fast_candidates:
        for c in charge_candidates:
            res = compute_pve_score(
                attacker_attack=atk,
                attacker_defense=dfn,
                attacker_hp=int(hp),
                fast_move=_build_fast_pve(f),
                charge_moves=[_build_charge_pve(c)],
                target_defense=180.0,
                incoming_dps=35.0,
                alpha=0.6,
            )
            val = float(res.get("value", 0.0))
            if val > pve_best[2]:
                pve_best = (f["name"], c["name"], val)

    # PvP: pick fast + two charges that maximize MP component
    pvp_best = (None, None, None, 0.0)
    for f in fast_candidates:
        fmv = _build_fast_pvp(f)
        for i in range(len(charge_candidates)):
            for j in range(i, len(charge_candidates)):
                charges = [charge_candidates[i]]
                if j != i:
                    charges.append(charge_candidates[j])
                cmv = [_build_charge_pvp(m) for m in charges]
                mp = move_pressure(fmv, cmv, bait_probability=0.5)
                if mp > pvp_best[3]:
                    names = [m["name"] for m in charges]
                    pvp_best = (f["name"], names[0], (names[1] if len(names) > 1 else None), mp)

    return BestMoves(
        pve_fast=pve_best[0] or fast_candidates[0]["name"],
        pve_charge1=pve_best[1] or charge_candidates[0]["name"],
        pve_charge2=None,
        pvp_fast=pvp_best[0] or fast_candidates[0]["name"],
        pvp_charge1=pvp_best[1] or charge_candidates[0]["name"],
        pvp_charge2=pvp_best[2],
    )

