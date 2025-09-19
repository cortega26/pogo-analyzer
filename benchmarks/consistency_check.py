"""Consistency check against external references (manual or curated).

This small test-like script evaluates a set of Pokémon and moves using the
PoGo Analyzer PvE functions and compares the results to reference metrics from
specialized sites (if provided). It prints a summary and writes a CSV report.

Usage:
  python benchmarks/consistency_check.py \
      --reference benchmarks/reference_external.csv \
      --out benchmarks/consistency_report.csv

If --reference is omitted or the file is missing, the script writes a
template CSV you can fill in with external values (reference_dps, source).
Then re-run the script to compute deltas and rank correlations.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from pogo_analyzer.data.base_stats import load_default_base_stats
from pogo_analyzer.formulas import effective_stats
from pogo_analyzer.pve import ChargeMove, FastMove, compute_pve_score


# Sample set of ~25 popular raid attackers with reasonable PvE moves.
# For consistency, we evaluate at Level 40, IVs 15/15/15, non-Shadow unless noted.
# You can add more species or adjust moves as needed for your comparison.
SAMPLES: list[dict[str, Any]] = [
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
    {"species": "Shadow Mewtwo", "fast": "Confusion",
        "charge": "Psystrike", "shadow": True},
    {"species": "Shadow Machamp", "fast": "Counter",
        "charge": "Dynamic Punch", "shadow": True},
]


def _load_moves() -> Mapping[str, Any]:
    """Load normalized moves JSON (from pogo-gamemaster-import)."""

    import json

    path = Path("normalized_data/normalized_moves.json")
    if not path.is_file():
        raise SystemExit(
            "normalized_data/normalized_moves.json is missing.\n"
            "Run: pogo-gamemaster-import --out-dir normalized_data"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    # Sanity check and hint if buckets look empty
    n_fast = len(payload.get("fast", []) or [])
    n_charge = len(payload.get("charge", []) or [])
    if n_fast == 0 or n_charge == 0:
        print(
            "Warning: normalized_moves.json buckets look sparse (fast=%d, charge=%d).\n"
            "         If this file was not created by pogo-gamemaster-import, consider regenerating it:\n"
            "         pogo-gamemaster-import --out-dir normalized_data"
            % (n_fast, n_charge)
        )
    return payload


def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _find_move(db: Mapping[str, Any], name: str) -> Mapping[str, Any] | None:
    """Robust name match across both buckets using alnum-normalization."""
    target = _norm(name)
    for bucket in ("fast", "charge"):
        for m in (db.get(bucket, []) or []):
            if _norm(str(m.get("name", ""))) == target:
                return m
    return None


def _stab(move_type: str | None, species_types: Iterable[str]) -> bool:
    if not move_type:
        return False
    low = move_type.strip().lower()
    return any((t or "").strip().lower() == low for t in species_types)


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    """Return Spearman rank correlation for xs vs ys (or None if invalid)."""

    if len(xs) != len(ys) or len(xs) < 2:
        return None

    def _ranks(values: list[float]) -> list[float]:
        # Average ranks for ties
        indexed = sorted([(v, i)
                         for i, v in enumerate(values)], key=lambda t: t[0])
        ranks = [0.0] * len(values)
        i = 0
        while i < len(indexed):
            j = i
            while j + 1 < len(indexed) and indexed[j + 1][0] == indexed[i][0]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[indexed[k][1]] = avg_rank
            i = j + 1
        return ranks

    rx = _ranks(xs)
    ry = _ranks(ys)
    mean_rx = sum(rx) / len(rx)
    mean_ry = sum(ry) / len(ry)
    num = sum((a - mean_rx) * (b - mean_ry) for a, b in zip(rx, ry))
    denx = math.sqrt(sum((a - mean_rx) ** 2 for a in rx))
    deny = math.sqrt(sum((b - mean_ry) ** 2 for b in ry))
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def _ensure_template(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "species",
            "variant",
            "fast_move",
            "charge_move",
            "reference_dps",
            "reference_source",
        ])
        for r in rows:
            w.writerow([
                r["species"],
                ("Shadow" if r.get("shadow") else "Normal"),
                r["fast"],
                r["charge"],
                "",
                "",
            ])
    print("Wrote template:", path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    default_out = Path(__file__).resolve().parent / "consistency_report.csv"
    p.add_argument("--reference", type=Path,
                   help="CSV with columns: species,variant,fast_move,charge_move,reference_dps,reference_source")
    p.add_argument("--out", type=Path, default=default_out)
    p.add_argument("--level", type=float, default=40.0,
                   help="Level for A/D/H computation (default: 40.0)")
    return p.parse_args()


def main() -> Path:
    args = parse_args()
    repo = load_default_base_stats()
    moves_db = _load_moves()

    # Prepare optional reference map
    ref_map: dict[tuple[str, str, str, str], tuple[float, str]] = {}
    if args.reference is None or not args.reference.is_file():
        # Write a template and proceed without reference comparisons
        tmpl = args.reference or (Path(__file__).resolve().parent / "reference_external.csv")
        _ensure_template(tmpl, SAMPLES)
    else:
        with args.reference.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                try:
                    key = (
                        (row.get("species") or "").strip(),
                        (row.get("variant") or "Normal").strip(),
                        (row.get("fast_move") or "").strip(),
                        (row.get("charge_move") or "").strip(),
                    )
                    ref_dps = float(row.get("reference_dps", "") or "nan")
                    source = (row.get("reference_source") or "").strip()
                    if not math.isnan(ref_dps):
                        ref_map[key] = (ref_dps, source)
                except Exception:
                    continue

    rows: list[dict[str, Any]] = []
    for case in SAMPLES:
        species = case["species"]
        variant = "Shadow" if case.get("shadow") else "Normal"
        try:
            bs = repo.get(species)
        except KeyError:
            print("Skipping (unknown species):", species)
            continue

        # Build A/D/H (15/15/15 IVs at chosen level); apply Shadow if selected
        A, D, H = effective_stats(
            bs.attack,
            bs.defense,
            bs.stamina,
            15,
            15,
            15,
            float(args.level),
            is_shadow=bool(case.get("shadow")),
            is_best_buddy=False,
        )

        # Look up moves
        f = _find_move(moves_db, case["fast"])  # search both buckets
        c = _find_move(moves_db, case["charge"])  # search both buckets
        if not f or not c:
            print("Skipping (missing move):", species,
                  case["fast"], case["charge"])
            continue

        fast = FastMove(
            name=f["name"],
            power=float(f.get("pve_power", 0.0)),
            energy_gain=float(f.get("pve_energy_gain", 0.0)),
            duration=float(f.get("pve_duration_s", 1.0) or 1.0),
            stab=_stab(str(f.get("type", "")), bs.types),
        )
        charge = ChargeMove(
            name=c["name"],
            power=float(c.get("pve_power", 0.0)),
            energy_cost=float(c.get("pve_energy_gain", 50.0) or 50.0),
            duration=float(c.get("pve_duration_s", 1.0) or 1.0),
            stab=_stab(str(c.get("type", "")), bs.types),
        )

        pve = compute_pve_score(
            A,
            D,
            int(H),
            fast,
            [charge],
            target_defense=180.0,
            incoming_dps=35.0,
            alpha=0.6,
        )

        our_dps = float(pve["dps"])
        our_tdo = float(pve["tdo"])
        our_val = float(pve["value"])

        ref_key = (species, variant, case["fast"], case["charge"])
        ref = ref_map.get(ref_key)
        if ref:
            ref_dps, source = ref
            diff = our_dps - ref_dps
            rel = (diff / ref_dps) if ref_dps else float("nan")
        else:
            ref_dps, source, diff, rel = float(
                "nan"), "", float("nan"), float("nan")

        rows.append(
            {
                "species": species,
                "variant": variant,
                "fast_move": fast.name,
                "charge_move": charge.name,
                "our_dps": round(our_dps, 3),
                "our_tdo": round(our_tdo, 3),
                "our_value": round(our_val, 3),
                "reference_dps": (None if math.isnan(ref_dps) else ref_dps),
                "dps_delta": (None if math.isnan(diff) else round(diff, 3)),
                "dps_rel_error": (None if math.isnan(rel) else round(rel, 4)),
                "reference_source": source,
            }
        )

    # Rank correlation when references exist
    ref_pairs = [(r["our_dps"], r["reference_dps"])
                 for r in rows if r["reference_dps"] is not None]
    spearman = None
    if ref_pairs:
        xs = [p[0] for p in ref_pairs]
        ys = [p[1] for p in ref_pairs]
        spearman = _spearman(xs, ys)

    # Write report
    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "species",
                "variant",
                "fast_move",
                "charge_move",
                "our_dps",
                "our_tdo",
                "our_value",
                "reference_dps",
                "dps_delta",
                "dps_rel_error",
                "reference_source",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print("Saved:", out.resolve())
    if spearman is not None:
        print(
            f"Spearman rank correlation (our DPS vs reference): {spearman:.4f}")
    else:
        print("No reference values found. Fill the template and rerun for correlation.")

    return out


if __name__ == "__main__":  # pragma: no cover
    main()
