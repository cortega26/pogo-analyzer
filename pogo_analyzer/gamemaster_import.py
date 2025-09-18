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

    # Build move maps
    moves = gm.get("moves", [])
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
        # Fast moves have pvpTurns > 0 in gamemaster, charged have pvpEnergy < 0
        # Track ID->name for later species legacy/elite mapping
        id_to_name[mid] = entry["name"]
        if entry["pvp_turns"] > 0:
            fast_moves[entry["name"]] = entry
        else:
            charge_moves[entry["name"]] = entry

    # Species and learnsets
    species_payload = []
    learnsets: dict[str, dict[str, list[str]]] = {}
    exclusive_moves: dict[str, Any] = {}
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
        learnsets[name] = {
            "fast": [m for m in pkmn.get("fastMoves", []) if m],
            "charge": [m for m in pkmn.get("chargedMoves", []) if m],
        }

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

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    species_path = out_dir / "normalized_species.json"
    moves_path = out_dir / "normalized_moves.json"
    learnsets_path = out_dir / "learnsets.json"
    exclusives_path = out_dir / "exclusive_moves.json"

    species_path.write_text(json.dumps({"species": species_payload}, indent=2) + "\n", encoding="utf-8")
    moves_path.write_text(
        json.dumps(
            {
                "fast": list(fast_moves.values()),
                "charge": list(charge_moves.values()),
            },
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
    print("Saved:", moves_path.resolve())
    print("Saved:", learnsets_path.resolve())
    return species_path, moves_path, learnsets_path


if __name__ == "__main__":  # pragma: no cover
    try:
        main(sys.argv[1:])
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)
