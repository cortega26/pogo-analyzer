"""Quick, self-contained PvE consistency check.

Goal: Be dead-simple to run. Uses normalized_data/normalized_moves.json when
available. If not, falls back to a small built-in move table for the sample
set so you don't need any preparation.

Usage (from repo root):
  python benchmarks/quick_consistency.py
  # optionally compare to references you fill in:
  python benchmarks/quick_consistency.py --reference benchmarks/reference_external.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from pogo_analyzer.data.base_stats import load_default_base_stats
from pogo_analyzer.formulas import effective_stats
from pogo_analyzer.pve import ChargeMove, FastMove, compute_pve_score


# Minimal fallback PvE move data for the sample set (approximate canonical values).
# Only used when normalized_data/normalized_moves.json is missing.
FALLBACK_MOVES: dict[str, dict[str, float | str]] = {
    # fast: name -> {type, pve_power, pve_energy_gain, pve_duration_s}
    "Confusion": {"type": "psychic", "pve_power": 20, "pve_energy_gain": 15, "pve_duration_s": 1.6},
    "Dragon Tail": {"type": "dragon", "pve_power": 15, "pve_energy_gain": 9, "pve_duration_s": 1.1},
    "Shadow Claw": {"type": "ghost", "pve_power": 9, "pve_energy_gain": 6, "pve_duration_s": 0.7},
    "Smack Down": {"type": "rock", "pve_power": 16, "pve_energy_gain": 8, "pve_duration_s": 0.8},
    "Bullet Punch": {"type": "steel", "pve_power": 9, "pve_energy_gain": 10, "pve_duration_s": 0.9},
    "Counter": {"type": "fighting", "pve_power": 12, "pve_energy_gain": 8, "pve_duration_s": 0.9},
    "Waterfall": {"type": "water", "pve_power": 16, "pve_energy_gain": 8, "pve_duration_s": 0.9},
    "Mud Shot": {"type": "ground", "pve_power": 5, "pve_energy_gain": 9, "pve_duration_s": 0.6},
    "Fire Fang": {"type": "fire", "pve_power": 12, "pve_energy_gain": 8, "pve_duration_s": 0.9},
    "Dragon Breath": {"type": "dragon", "pve_power": 4, "pve_energy_gain": 3, "pve_duration_s": 0.5},
    "Fire Spin": {"type": "fire", "pve_power": 14, "pve_energy_gain": 10, "pve_duration_s": 1.1},
    "Bite": {"type": "dark", "pve_power": 6, "pve_energy_gain": 4, "pve_duration_s": 0.5},
    "Mud-Slap": {"type": "ground", "pve_power": 18, "pve_energy_gain": 12, "pve_duration_s": 1.4},
    "Snarl": {"type": "dark", "pve_power": 12, "pve_energy_gain": 14, "pve_duration_s": 1.1},
    "Powder Snow": {"type": "ice", "pve_power": 6, "pve_energy_gain": 15, "pve_duration_s": 1.0},
    "Razor Leaf": {"type": "grass", "pve_power": 13, "pve_energy_gain": 7, "pve_duration_s": 1.0},

    # charge: name -> {type, pve_power, pve_energy_cost, pve_duration_s}
    "Psystrike": {"type": "psychic", "pve_power": 90, "pve_energy_cost": 50, "pve_duration_s": 2.3},
    "Outrage": {"type": "dragon", "pve_power": 110, "pve_energy_cost": 50, "pve_duration_s": 3.9},
    "Shadow Ball": {"type": "ghost", "pve_power": 100, "pve_energy_cost": 50, "pve_duration_s": 3.0},
    "Stone Edge": {"type": "rock", "pve_power": 100, "pve_energy_cost": 55, "pve_duration_s": 2.3},
    "Rock Wrecker": {"type": "rock", "pve_power": 110, "pve_energy_cost": 50, "pve_duration_s": 2.3},
    "Meteor Mash": {"type": "steel", "pve_power": 100, "pve_energy_cost": 50, "pve_duration_s": 2.6},
    "Dynamic Punch": {"type": "fighting", "pve_power": 90, "pve_energy_cost": 50, "pve_duration_s": 2.7},
    "Aura Sphere": {"type": "fighting", "pve_power": 90, "pve_energy_cost": 50, "pve_duration_s": 2.4},
    "Surf": {"type": "water", "pve_power": 65, "pve_energy_cost": 50, "pve_duration_s": 1.7},
    "Precipice Blades": {"type": "ground", "pve_power": 130, "pve_energy_cost": 50, "pve_duration_s": 2.6},
    "Fusion Flare": {"type": "fire", "pve_power": 90, "pve_energy_cost": 45, "pve_duration_s": 2.6},
    "Wild Charge": {"type": "electric", "pve_power": 90, "pve_energy_cost": 50, "pve_duration_s": 2.6},
    "Overheat": {"type": "fire", "pve_power": 160, "pve_energy_cost": 100, "pve_duration_s": 4.0},
    "Brutal Swing": {"type": "dark", "pve_power": 65, "pve_energy_cost": 40, "pve_duration_s": 1.9},
    "Earth Power": {"type": "ground", "pve_power": 100, "pve_energy_cost": 55, "pve_duration_s": 3.5},
    "Drill Run": {"type": "ground", "pve_power": 80, "pve_energy_cost": 50, "pve_duration_s": 2.3},
    "Foul Play": {"type": "dark", "pve_power": 70, "pve_energy_cost": 45, "pve_duration_s": 2.0},
    "Avalanche": {"type": "ice", "pve_power": 90, "pve_energy_cost": 45, "pve_duration_s": 2.7},
    "Grass Knot": {"type": "grass", "pve_power": 90, "pve_energy_cost": 50, "pve_duration_s": 2.6},
    "Rock Slide": {"type": "rock", "pve_power": 80, "pve_energy_cost": 45, "pve_duration_s": 2.7},
    "Leaf Blade": {"type": "grass", "pve_power": 70, "pve_energy_cost": 35, "pve_duration_s": 2.0},
}


SAMPLES = [
    {"species": "Mewtwo", "fast": "Confusion", "charge": "Psystrike"},
    {"species": "Rayquaza", "fast": "Dragon Tail", "charge": "Outrage"},
    {"species": "Dragonite", "fast": "Dragon Tail", "charge": "Outrage"},
    {"species": "Gengar", "fast": "Shadow Claw", "charge": "Shadow Ball"},
    {"species": "Tyranitar", "fast": "Smack Down", "charge": "Stone Edge"},
    {"species": "Rhyperior", "fast": "Smack Down", "charge": "Rock Wrecker"},
    {"species": "Metagross", "fast": "Bullet Punch", "charge": "Meteor Mash"},
    {"species": "Machamp", "fast": "Counter", "charge": "Dynamic Punch"},
    {"species": "Lucario", "fast": "Counter", "charge": "Aura Sphere"},
    {"species": "Kyogre", "fast": "Waterfall", "charge": "Surf"},
    {"species": "Groudon", "fast": "Mud Shot", "charge": "Precipice Blades"},
    {"species": "Reshiram", "fast": "Fire Fang", "charge": "Fusion Flare"},
    {"species": "Zekrom", "fast": "Dragon Breath", "charge": "Wild Charge"},
    {"species": "Chandelure", "fast": "Fire Spin", "charge": "Overheat"},
    {"species": "Hydreigon", "fast": "Bite", "charge": "Brutal Swing"},
    {"species": "Garchomp", "fast": "Mud Shot", "charge": "Earth Power"},
    {"species": "Excadrill", "fast": "Mud-Slap", "charge": "Drill Run"},
    {"species": "Weavile", "fast": "Snarl", "charge": "Foul Play"},
    {"species": "Mamoswine", "fast": "Powder Snow", "charge": "Avalanche"},
    {"species": "Roserade", "fast": "Razor Leaf", "charge": "Grass Knot"},
    {"species": "Rampardos", "fast": "Smack Down", "charge": "Rock Slide"},
    {"species": "Kartana", "fast": "Razor Leaf", "charge": "Leaf Blade"},
]


def _load_moves_payload() -> Mapping[str, Any] | None:
    path = Path("normalized_data/normalized_moves.json")
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload
    except Exception:
        return None


def _lookup_move(payload: Mapping[str, Any] | None, name: str) -> dict[str, Any] | None:
    if payload is not None:
        low = name.lower()
        for bucket in ("fast", "charge"):
            for m in payload.get(bucket, []) or []:
                if str(m.get("name", "")).strip().lower() == low:
                    if bucket == "fast":
                        return {
                            "type": m.get("type"),
                            "pve_power": m.get("pve_power", 0.0),
                            "pve_energy_gain": m.get("pve_energy_gain", 0.0),
                            "pve_duration_s": m.get("pve_duration_s", 1.0),
                        }
                    else:
                        # normalize to fallback schema keys
                        cost = m.get("pve_energy_gain", 50.0)
                        return {
                            "type": m.get("type"),
                            "pve_power": m.get("pve_power", 0.0),
                            "pve_energy_cost": cost if isinstance(cost, (int, float)) else 50.0,
                            "pve_duration_s": m.get("pve_duration_s", 1.0),
                        }
    # fallback table
    return FALLBACK_MOVES.get(name)


def _merge_with_fallback(name: str, data: dict[str, Any] | None, *, is_fast: bool) -> dict[str, Any] | None:
    fb = FALLBACK_MOVES.get(name)
    if data is None and fb is None:
        return None
    if data is None:
        return dict(fb)  # type: ignore[arg-type]
    merged = dict(data)
    if fb:
        # Adopt fallback type when missing
        if not merged.get("type"):
            merged["type"] = fb.get("type")
        # Duration must be positive
        dur_key = "pve_duration_s"
        try:
            dur_val = float(merged.get(dur_key, 0) or 0)
        except Exception:
            dur_val = 0.0
        if dur_val <= 0:
            merged[dur_key] = fb.get(dur_key, 1.0)
        # Energy and power fallbacks if unset
        if is_fast:
            if merged.get("pve_energy_gain") in (None, "", 0, 0.0):
                merged["pve_energy_gain"] = fb.get("pve_energy_gain", 0.0)
            if merged.get("pve_power") in (None, ""):
                merged["pve_power"] = fb.get("pve_power", 0.0)
        else:
            cost = merged.get("pve_energy_cost")
            try:
                cost_f = float(cost) if cost is not None else 0.0
            except Exception:
                cost_f = 0.0
            if cost_f <= 0:
                merged["pve_energy_cost"] = fb.get("pve_energy_cost", 50.0)
            if merged.get("pve_power") in (None, ""):
                merged["pve_power"] = fb.get("pve_power", 0.0)
    # Final safety clamps
    merged["pve_duration_s"] = max(0.1, float(merged.get("pve_duration_s", 1.0) or 1.0))
    if is_fast:
        merged["pve_energy_gain"] = float(merged.get("pve_energy_gain", 0.0) or 0.0)
    else:
        ec = merged.get("pve_energy_cost", 50.0)
        try:
            ecf = float(ec)
        except Exception:
            ecf = 50.0
        merged["pve_energy_cost"] = max(1.0, ecf)
    return merged


def _stab(move_type: str | None, species_types: Iterable[str]) -> bool:
    if not move_type:
        return False
    return any((t or "").strip().lower() == (move_type or "").strip().lower() for t in species_types)


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    def _ranks(values: list[float]) -> list[float]:
        idx = sorted([(v, i) for i, v in enumerate(values)], key=lambda t: t[0])
        ranks = [0.0] * len(values)
        i = 0
        while i < len(idx):
            j = i
            while j + 1 < len(idx) and idx[j + 1][0] == idx[i][0]:
                j += 1
            r = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[idx[k][1]] = r
            i = j + 1
        return ranks
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    deny = math.sqrt(sum((b - my) ** 2 for b in ry))
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    default_out = Path(__file__).resolve().parent / "quick_consistency_report.csv"
    default_ref = Path(__file__).resolve().parent / "reference_external.csv"
    p.add_argument("--reference", type=Path, help="CSV: species,fast_move,charge_move,reference_dps,reference_source")
    p.add_argument("--out", type=Path, default=default_out)
    p.add_argument("--level", type=float, default=40.0)
    p.add_argument("--bootstrap-ref", action="store_true", help="Write a reference CSV using our own DPS (sanity check).")
    return p.parse_args()


def main() -> Path:
    args = parse_args()
    repo = load_default_base_stats()
    payload = _load_moves_payload()

    ref_map: dict[tuple[str, str, str], tuple[float, str]] = {}
    tmpl = args.reference or (Path(__file__).resolve().parent / "reference_external.csv")
    if args.reference is None or not args.reference.is_file():
        tmpl.parent.mkdir(parents=True, exist_ok=True)
        if args.bootstrap_ref:
            # We'll fill this later with our own results; create empty now
            with tmpl.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["species", "fast_move", "charge_move", "reference_dps", "reference_source"])
                for r in SAMPLES:
                    w.writerow([r["species"], r["fast"], r["charge"], "", ""]) 
            print("Wrote template (will bootstrap after compute):", tmpl)
        else:
            with tmpl.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["species", "fast_move", "charge_move", "reference_dps", "reference_source"])
                for r in SAMPLES:
                    w.writerow([r["species"], r["fast"], r["charge"], "", ""]) 
            print("Wrote template:", tmpl)
    else:
        with args.reference.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                key = (
                    (row.get("species") or "").strip(),
                    (row.get("fast_move") or "").strip(),
                    (row.get("charge_move") or "").strip(),
                )
                try:
                    ref_dps = float(row.get("reference_dps", "") or "nan")
                except Exception:
                    ref_dps = float("nan")
                src = (row.get("reference_source") or "").strip()
                if not math.isnan(ref_dps):
                    ref_map[key] = (ref_dps, src)

    rows: list[dict[str, Any]] = []
    for case in SAMPLES:
        species = case["species"]
        try:
            bs = repo.get(species)
        except KeyError:
            print("Skipping (unknown species):", species)
            continue
        A, D, H = effective_stats(bs.attack, bs.defense, bs.stamina, 15, 15, 15, float(args.level), is_shadow=species.lower().startswith("shadow "), is_best_buddy=False)

        f_raw = _lookup_move(payload, case["fast"]) 
        c_raw = _lookup_move(payload, case["charge"]) 
        f = _merge_with_fallback(case["fast"], f_raw, is_fast=True)
        c = _merge_with_fallback(case["charge"], c_raw, is_fast=False)
        if not f or not c:
            print("Skipping (missing move):", species, case["fast"], case["charge"])
            continue

        fast = FastMove(
            name=case["fast"],
            power=float(f.get("pve_power", 0.0)),
            energy_gain=float(f.get("pve_energy_gain", 0.0)),
            duration=float(f.get("pve_duration_s", 1.0)),
            stab=_stab(str(f.get("type")), bs.types),
        )
        charge = ChargeMove(
            name=case["charge"],
            power=float(c.get("pve_power", 0.0)),
            energy_cost=float(c.get("pve_energy_cost", 50.0)),
            duration=float(c.get("pve_duration_s", 1.0)),
            stab=_stab(str(c.get("type")), bs.types),
        )

        pve = compute_pve_score(A, D, int(H), fast, [charge], target_defense=180.0, incoming_dps=35.0, alpha=0.6)
        our_dps = float(pve["dps"])
        our_tdo = float(pve["tdo"])
        our_val = float(pve["value"])

        key = (species, case["fast"], case["charge"]) 
        ref = ref_map.get(key)
        if ref:
            ref_dps, source = ref
            diff = our_dps - ref_dps
            rel = (diff / ref_dps) if ref_dps else float("nan")
        else:
            ref_dps, source, diff, rel = float("nan"), "", float("nan"), float("nan")

        rows.append({
            "species": species,
            "fast_move": fast.name,
            "charge_move": charge.name,
            "our_dps": round(our_dps, 3),
            "our_tdo": round(our_tdo, 3),
            "our_value": round(our_val, 3),
            "reference_dps": (None if math.isnan(ref_dps) else ref_dps),
            "dps_delta": (None if math.isnan(diff) else round(diff, 3)),
            "dps_rel_error": (None if math.isnan(rel) else round(rel, 4)),
            "reference_source": source,
        })

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["species", "fast_move", "charge_move", "our_dps", "our_tdo", "our_value", "reference_dps", "dps_delta", "dps_rel_error", "reference_source"]) 
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("Saved:", out.resolve())

    # Optional: bootstrap a reference file with our own DPS for a quick sanity check
    if args.bootstrap_ref:
        ref_path = args.reference or (Path(__file__).resolve().parent / "reference_external.csv")
        with ref_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["species", "fast_move", "charge_move", "reference_dps", "reference_source"])
            for r in rows:
                w.writerow([r["species"], r["fast_move"], r["charge_move"], r["our_dps"], "SELF-bootstrap"])
        print("Bootstrapped reference with our DPS:", ref_path)

    # Spearman correlation when ref data exists
    pairs = [(r["our_dps"], r["reference_dps"]) for r in rows if r["reference_dps"] is not None]
    if pairs:
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        sc = _spearman(xs, ys)
        if sc is not None:
            print(f"Spearman (our DPS vs reference): {sc:.4f}")
        else:
            print("Insufficient variance for rank correlation.")
    else:
        print("No reference values found. Fill the template and rerun for correlation.")
    return out


if __name__ == "__main__":  # pragma: no cover
    main()
