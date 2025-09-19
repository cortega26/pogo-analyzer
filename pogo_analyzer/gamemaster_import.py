"""Import PvPoke gamemaster and normalize species, moves, learnsets, and exclusives.

Usage:
  pogo-gamemaster-import --out-dir normalized_data

This fetches the public gamemaster JSON and writes:
  - normalized_species.json
  - normalized_moves.json
  - learnsets.json
  - exclusive_moves.json (new)

Notes:
  - Respects network-only on explicit command; not used implicitly.
  - Outputs include PvE (power, duration_s, energy_gain) and PvP (damage, energy_gain, turns) plus move type.
  - ``exclusive_moves.json`` groups per-species legacy/elite moves by fast/charge. When PvPoke doesn't
    include legacy/elite lists for a species, the entry is omitted.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


GM_URL = "https://raw.githubusercontent.com/pvpoke/pvpoke/master/src/data/gamemaster.json"


def _fetch_gamemaster() -> Mapping[str, Any]:
    import urllib.request

    with urllib.request.urlopen(GM_URL, timeout=30) as resp:  # nosec - public static file
        data = resp.read().decode("utf-8")
    return json.loads(data)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, required=True)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> tuple[Path, Path, Path]:
    args = parse_args(argv)
    gm = _fetch_gamemaster()

    # Build move index (do not classify yet)
    moves = gm.get("moves", [])
    all_moves_by_name: dict[str, dict[str, Any]] = {}
    fast_moves: dict[str, dict[str, Any]] = {}
    charge_moves: dict[str, dict[str, Any]] = {}
    id_to_name: dict[str, str] = {}
    for m in moves:
        mid = m.get("moveId")
        if not mid:
            continue
        entry = {
            "name": m.get("name", mid),
            "type": m.get("type", ""),
            # PvE
            "pve_power": float(m.get("power", 0) or 0),
            "pve_energy_gain": float((m.get("energy") or 0) * -1 if (m.get("energy") or 0) < 0 else (m.get("energyGain") or 0)),
            "pve_duration_s": float((m.get("durationMs") or 0) / 1000.0),
            # PvP
            "pvp_damage": float(m.get("pvpPower", 0) or 0),
            "pvp_energy_gain": float((m.get("pvpEnergy") or 0) * -1 if (m.get("pvpEnergy") or 0) < 0 else (m.get("pvpEnergyGain") or 0)),
            "pvp_turns": int(m.get("pvpTurns", 0) or 0),
        }
        # Track ID->name for later mapping and defer classification
        id_to_name[mid] = entry["name"]
        all_moves_by_name[entry["name"]] = entry

    # Species and learnsets (+ collect fast/charge membership from species learnsets)
    species_payload = []
    learnsets: dict[str, dict[str, list[str]]] = {}
    exclusive_moves: dict[str, Any] = {}
    fast_member_names: set[str] = set()
    charge_member_names: set[str] = set()
    for pkmn in gm.get("pokemon", []):
        name = pkmn.get("speciesName")
        if not name:
            continue
        base = pkmn.get("baseStats", {})
        types = [t for t in pkmn.get("types", []) if t]
        species_payload.append(
            {
                "name": name,
                "base_attack": int(base.get("atk", 0) or 0),
                "base_defense": int(base.get("def", 0) or 0),
                "base_stamina": int(base.get("hp", 0) or 0),
                "types": types,
            }
        )
        raw_fast = [m for m in pkmn.get("fastMoves", []) if m]
        raw_charge = [m for m in pkmn.get("chargedMoves", []) if m]
        # Map IDs -> human names when possible
        fast_names = [id_to_name.get(mid, mid) for mid in raw_fast]
        charge_names = [id_to_name.get(mid, mid) for mid in raw_charge]
        learnsets[name] = {"fast": fast_names, "charge": charge_names}
        fast_member_names.update(fast_names)
        charge_member_names.update(charge_names)

        # Legacy/Elite per species -> exclusive moves
        legacy_ids = set(pkmn.get("legacyMoves", []) or [])
        elite_ids = set(pkmn.get("eliteMoves", []) or [])
        if legacy_ids or elite_ids:
            # Map IDs to human names, then split by fast/charge using the move tables built above
            legacy_names = {id_to_name.get(mid, mid) for mid in legacy_ids}
            elite_names = {id_to_name.get(mid, mid) for mid in elite_ids}
            legacy_fast = sorted(n for n in legacy_names if n in fast_moves)
            legacy_charge = sorted(n for n in legacy_names if n in charge_moves)
            elite_fast = sorted(n for n in elite_names if n in fast_moves)
            elite_charge = sorted(n for n in elite_names if n in charge_moves)
            # Union sets for convenience
            fast_union = sorted(set(legacy_fast) | set(elite_fast))
            charge_union = sorted(set(legacy_charge) | set(elite_charge))
            exclusive_moves[name] = {
                "fast": fast_union,
                "charge": charge_union,
                "legacy_fast": legacy_fast,
                "legacy_charge": legacy_charge,
                "elite_fast": elite_fast,
                "elite_charge": elite_charge,
            }

    # Finalize move classification based on species membership first, then fall back to pvp fields
    for mv_name, entry in all_moves_by_name.items():
        if mv_name in fast_member_names and mv_name not in charge_member_names:
            fast_moves[mv_name] = entry
        elif mv_name in charge_member_names and mv_name not in fast_member_names:
            charge_moves[mv_name] = entry
        elif mv_name in fast_member_names and mv_name in charge_member_names:
            # Appears in both lists in some edge cases (forms) — prefer charge if energy negative in PvE/PvP
            # else put in fast
            if entry.get("pve_energy_gain", 0) < 0 or entry.get("pvp_energy_gain", 0) < 0:
                charge_moves[mv_name] = entry
            else:
                fast_moves[mv_name] = entry
        else:
            # Fallback classification
            if entry.get("pvp_turns", 0) > 0 or entry.get("pvp_energy_gain", 0) > 0:
                fast_moves[mv_name] = entry
            else:
                charge_moves[mv_name] = entry

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    species_path = out_dir / "normalized_species.json"
    moves_path = out_dir / "normalized_moves.json"
    learnsets_path = out_dir / "learnsets.json"
    exclusives_path = out_dir / "exclusive_moves.json"

    species_path.write_text(json.dumps({"species": species_payload}, indent=2) + "\n", encoding="utf-8")
    moves_payload = {
        "fast": list(fast_moves.values()),
        "charge": list(charge_moves.values()),
    }
    moves_path.write_text(
        json.dumps(
            moves_payload,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    learnsets_path.write_text(json.dumps(learnsets, indent=2) + "\n", encoding="utf-8")
    # Only write exclusives file when we have data
    if exclusive_moves:
        exclusives_path.write_text(
            json.dumps(
                {
                    "metadata": {"source": "pvpoke-gamemaster", "notes": "Per-species legacy/elite moves parsed from gamemaster"},
                    "exclusives": exclusive_moves,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print("Saved:", exclusives_path.resolve())

    print("Saved:", species_path.resolve())
    print(
        "Saved:", moves_path.resolve(),
        f"(fast={len(moves_payload['fast'])}, charge={len(moves_payload['charge'])})",
    )
    print("Saved:", learnsets_path.resolve())
    return species_path, moves_path, learnsets_path


if __name__ == "__main__":  # pragma: no cover
    try:
        main(sys.argv[1:])
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)
