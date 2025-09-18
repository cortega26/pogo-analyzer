"""
Generate a PvP scoreboard from normalized species/moves/learnsets.

This command consumes the offline-normalized JSON files and produces
`pvp_scoreboard.csv` ranking species by V_PvP for a given league cap.

It does not alter PvE defaults and lives alongside the raid scoreboard.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from pogo_analyzer.cpm_table import get_cpm
from pogo_analyzer.formulas import effective_stats
from pogo_analyzer.pvp import (
    DEFAULT_LEAGUE_CONFIGS,
    LeagueConfig,
    PvpChargeMove,
    PvpFastMove,
    compute_pvp_score,
)


def _parse_kv_float_map(expr: str | None) -> dict[str, float] | None:
    if not expr:
        return None
    parts = [p.strip() for p in expr.split(',') if p.strip()]
    out: dict[str, float] = {}
    for part in parts:
        k, sep, v = part.partition('=')
        if not sep:
            raise ValueError("Expected key=value pairs in --bait-model")
        k = k.strip()
        if not k:
            raise ValueError("Empty key in --bait-model")
        out[k] = float(v.strip())
    return out


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--species", required=True, type=Path, help="Normalized species JSON from pogo-data-refresh.")
    p.add_argument("--moves", required=True, type=Path, help="Normalized moves JSON from pogo-data-refresh.")
    p.add_argument("--learnsets", required=True, type=Path, help="JSON mapping species -> {fast:[], charge:[]}.")
    p.add_argument("--output-dir", type=Path, help="Directory for the output CSV.")
    p.add_argument("--csv-name", help="File name for the PvP CSV (default: pvp_scoreboard.csv).")

    # League and scoring knobs
    p.add_argument("--league-cap", type=int, help="CP cap for the league (1500, 2500, or <=0 for Master).")
    p.add_argument("--beta", type=float, help="Blend factor between SP and MP (default per league=0.52).")
    p.add_argument("--sp-ref", dest="sp_ref", type=float, help="Override stat product reference.")
    p.add_argument("--mp-ref", dest="mp_ref", type=float, help="Override move pressure reference.")
    p.add_argument("--shield-weights", type=float, nargs=3, metavar=("W0", "W1", "W2"), help="Blend 0/1/2 shield scenarios.")
    p.add_argument("--bait-prob", dest="bait_prob", type=float, help="Static bait probability if no model is used.")
    p.add_argument("--pvp-energy-weight", dest="energy_weight", type=float, help="kappa: fast move energy weight.")
    p.add_argument("--pvp-buff-weight", dest="buff_weight", type=float, help="lambda: charge move buff EV weight.")
    p.add_argument("--bait-model", help="Override sigmoid bait model as a=,b=,c=,d=.")
    p.add_argument("--enhanced-defaults", action="store_true", help="Opt-in to enhanced pvp defaults (kappa/lambda/shields/model).")

    # IVs and optimization
    p.add_argument("--ivs", type=int, nargs=3, metavar=("ATK", "DEF", "STA"), help="Assumed IVs for all species (default: 15 15 15).")
    p.add_argument("--iv-mode", choices=["fixed", "max-sp"], default="fixed", help="Use provided IVs or search for max-stat-product IVs under cap.")
    p.add_argument("--iv-floor", type=int, default=0, help="Minimum IV value to allow during search (default: 0).")

    return p.parse_args(argv)


def _resolve_league_key(league_cap: int | None) -> str:
    if league_cap is None:
        return "great"
    if league_cap == 1500:
        return "great"
    if league_cap == 2500:
        return "ultra"
    if league_cap <= 0:
        return "master"
    valid = {cfg.cp_cap for cfg in DEFAULT_LEAGUE_CONFIGS.values() if cfg.cp_cap is not None}
    raise ValueError(f"Unsupported league cap; valid values are 1500, 2500, or <=0 for Master. Known: {sorted(valid)}")


def _cap_level_for_species(base_a: int, base_d: int, base_s: int, ivs: tuple[int, int, int], cap: int) -> float:
    # Find highest level in [1,51] s.t. CP <= cap (or max 51 when cap<=0)
    if cap <= 0:
        return 51.0
    best_level = 1.0
    best_cp = -1
    for i in range(2, 103):
        level = i / 2
        try:
            cpm = get_cpm(level)
        except ValueError:
            continue
        atk = (base_a + ivs[0]) * cpm
        dfn = (base_d + ivs[1]) * cpm
        sta = (base_s + ivs[2]) * cpm
        cp = int((atk * (dfn ** 0.5) * (sta ** 0.5)) // 10)
        if cp <= cap and cp >= best_cp:
            best_cp = cp
            best_level = level
    return best_level


def _best_iv_and_level_under_cap(
    base_a: int,
    base_d: int,
    base_s: int,
    cap: int,
    iv_floor: int = 0,
) -> tuple[tuple[int, int, int], float]:
    """Brute-force search for IVs and level that maximise SP under the CP cap.

    Intended for small to medium datasets; for larger corpora consider caching
    or pruning. Defaults maintain performance by keeping this opt-in.
    """
    best: tuple[tuple[int, int, int], float, float] | None = None  # (ivs, level, SP)
    floors = max(0, int(iv_floor))
    for atk_iv in range(floors, 16):
        for def_iv in range(floors, 16):
            for sta_iv in range(floors, 16):
                ivs = (atk_iv, def_iv, sta_iv)
                level = _cap_level_for_species(base_a, base_d, base_s, ivs, cap)
                cpm = get_cpm(level)
                atk = (base_a + atk_iv) * cpm
                dfn = (base_d + def_iv) * cpm
                hp = int((base_s + sta_iv) * cpm)
                sp = atk * dfn * max(1, hp)
                if best is None or sp > best[2] + 1e-9:
                    best = (ivs, level, sp)
    assert best is not None
    return best[0], best[1]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_move_maps(moves_payload: Mapping[str, Any]) -> tuple[dict[str, PvpFastMove], dict[str, PvpChargeMove]]:
    fast_map: dict[str, PvpFastMove] = {}
    for row in moves_payload.get("fast", []):
        fast_map[str(row["name"])]= PvpFastMove(
            name=str(row["name"]),
            damage=float(row["damage"]),
            energy_gain=float(row["energy_gain"]),
            turns=int(row["turns"]),
        )
    charge_map: dict[str, PvpChargeMove] = {}
    for row in moves_payload.get("charge", []):
        charge_map[str(row["name"])]= PvpChargeMove(
            name=str(row["name"]),
            damage=float(row["damage"]),
            energy_cost=float(row["energy_cost"]),
            reliability=(float(row["reliability"]) if row.get("reliability") is not None else None),
            has_buff=bool(row.get("has_buff", False)),
        )
    return fast_map, charge_map


def main(argv: Sequence[str] | None = None) -> Path:
    args = parse_args(argv)

    species_payload = _load_json(args.species)
    moves_payload = _load_json(args.moves)
    learnsets_payload = _load_json(args.learnsets)

    species_rows = species_payload.get("species", species_payload)
    if not isinstance(species_rows, list):
        raise SystemExit("Species JSON must provide a 'species' list or be a list of rows.")

    try:
        league_key = _resolve_league_key(args.league_cap)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    cfg: LeagueConfig = DEFAULT_LEAGUE_CONFIGS[league_key]
    sp_ref = args.sp_ref if args.sp_ref is not None else cfg.stat_product_reference
    mp_ref = args.mp_ref if args.mp_ref is not None else cfg.move_pressure_reference
    beta = args.beta if args.beta is not None else 0.52
    if not (0.0 < beta < 1.0):
        raise SystemExit("--beta must be between 0 and 1 (exclusive).")

    try:
        bait_model = _parse_kv_float_map(args.bait_model)
    except ValueError as exc:
        raise SystemExit(f"Failed to parse --bait-model: {exc}") from exc
    if bait_model is None and args.enhanced_defaults:
        bait_model = {"a": 0.4, "b": -0.1, "c": 0.35, "d": 0.0}

    league_configs = DEFAULT_LEAGUE_CONFIGS
    if bait_model is not None:
        base = cfg
        league_configs = dict(DEFAULT_LEAGUE_CONFIGS)
        league_configs[league_key] = LeagueConfig(
            cp_cap=base.cp_cap,
            stat_product_reference=sp_ref,
            move_pressure_reference=mp_ref,
            bait_probability=base.bait_probability,
            shield_weights=base.shield_weights,
            bait_model=bait_model,
            cmp_threshold=base.cmp_threshold,
            cmp_eta=base.cmp_eta,
            coverage_theta=base.coverage_theta,
            anti_meta_mu=base.anti_meta_mu,
        )

    energy_weight = args.energy_weight if args.energy_weight is not None else (1.0 if args.enhanced_defaults else 0.35)
    buff_weight = args.buff_weight if args.buff_weight is not None else (0.6 if args.enhanced_defaults else 12.0)
    shield_weights = tuple(args.shield_weights) if args.shield_weights is not None else ((0.2, 0.5, 0.3) if args.enhanced_defaults else None)

    fast_map, charge_map = _build_move_maps(moves_payload)
    fixed_ivs = tuple(args.ivs) if args.ivs is not None else (15, 15, 15)

    rows: list[dict[str, Any]] = []

    for row in species_rows:
        try:
            name = str(row["name"]).strip()
            base_a = int(row["base_attack"])
            base_d = int(row["base_defense"])
            base_s = int(row["base_stamina"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SystemExit("Species row missing required fields.") from exc

        if not name:
            continue
        learnset = learnsets_payload.get(name)
        if not learnset:
            continue  # silently skip species without learnsets
        fast_names = [str(n) for n in learnset.get("fast", [])]
        charge_names = [str(n) for n in learnset.get("charge", [])]
        if not fast_names or not charge_names:
            continue
        try:
            fast_candidates = [fast_map[n] for n in fast_names]
            charge_candidates = [charge_map[n] for n in charge_names]
        except KeyError as exc:
            raise SystemExit(f"Unknown move in learnsets for {name}: {exc}") from exc

        # Resolve IVs and level under cap
        if args.iv_mode == "max-sp":
            ivs, level = _best_iv_and_level_under_cap(base_a, base_d, base_s, args.league_cap or 1500, args.iv_floor)
        else:
            ivs = fixed_ivs
            level = _cap_level_for_species(base_a, base_d, base_s, ivs, args.league_cap or 1500)

        atk, dfn, hp = effective_stats(base_a, base_d, base_s, ivs[0], ivs[1], ivs[2], level)

        # Enumerate fast x (best 1 or 2 charge) combos
        best: dict[str, Any] | None = None
        for fast in fast_candidates:
            # Try single-charge and pairs
            for r in [1, 2]:
                for charges in itertools.combinations(charge_candidates, r):
                    res = compute_pvp_score(
                        attack=atk,
                        defense=dfn,
                        stamina=hp,
                        fast_move=fast,
                        charge_moves=list(charges),
                        league=league_key,
                        beta=beta,
                        stat_product_reference=sp_ref,
                        move_pressure_reference=mp_ref,
                        bait_probability=args.bait_prob,
                        shield_weights=shield_weights,
                        energy_weight=energy_weight,
                        buff_weight=buff_weight,
                        league_configs=league_configs,
                    )
                    score = float(res["score"])  # type: ignore[assignment]
                    if best is None or score > best["Score"]:
                        best = {
                            "Species": name,
                            "League": league_key,
                            "Level": f"{level:.1f}",
                            "Attack": f"{atk:.2f}",
                            "Defense": f"{dfn:.2f}",
                            "HP": int(hp),
                            "Stat Product": f"{res['stat_product']:.2f}",
                            "SP_norm": f"{res['stat_product_normalised']:.4f}",
                            "Move Pressure": f"{res['move_pressure']:.2f}",
                            "MP_norm": f"{res['move_pressure_normalised']:.4f}",
                            "Score": score,
                            "Best Fast": fast.name,
                            "Best Charge 1": charges[0].name,
                            "Best Charge 2": charges[1].name if len(charges) > 1 else "",
                        }
        if best is not None:
            rows.append(best)

    # Output
    out_dir = args.output_dir or Path.cwd()
    csv_path = out_dir / (args.csv_name or "pvp_scoreboard.csv")
    if not rows:
        # Still write a header-only file for consistency
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "Species",
                    "League",
                    "Level",
                    "Attack",
                    "Defense",
                    "HP",
                    "Stat Product",
                    "SP_norm",
                    "Move Pressure",
                    "MP_norm",
                    "Score",
                    "Best Fast",
                    "Best Charge 1",
                    "Best Charge 2",
                ],
            )
            w.writeheader()
        print("Saved:", csv_path.resolve())
        return csv_path

    # Sort by Score desc
    rows.sort(key=lambda r: r["Score"], reverse=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("Saved:", csv_path.resolve())
    return csv_path


if __name__ == "__main__":  # pragma: no cover
    main()
