"""Offline data refresh and normalisation tool.

This CLI consumes pre-scraped JSON/CSV files describing species base stats and
PvP moves and emits validated, normalised JSON artifacts for downstream tools.

The tool does NOT scrape; it only validates and reshapes files you provide.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class SpeciesRow:
    name: str
    base_attack: int
    base_defense: int
    base_stamina: int


@dataclass(frozen=True)
class FastMoveRow:
    name: str
    damage: float
    energy_gain: float
    turns: int
    availability: str = "standard"


@dataclass(frozen=True)
class ChargeMoveRow:
    name: str
    damage: float
    energy_cost: float
    reliability: float | None = None
    has_buff: bool = False
    availability: str = "standard"


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON from {path}: {exc}") from exc


def _validate_species_entry(entry: Mapping[str, Any]) -> SpeciesRow:
    try:
        name = str(entry["name"]).strip()
        ba = int(entry["base_attack"])  # noqa: N806
        bd = int(entry["base_defense"])  # noqa: N806
        bs = int(entry["base_stamina"])  # noqa: N806
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Species row missing or invalid fields: name/base_attack/base_defense/base_stamina") from exc
    if not name:
        raise ValueError("Species name cannot be empty")
    if min(ba, bd, bs) <= 0:
        raise ValueError("Species base stats must be positive integers")
    return SpeciesRow(name, ba, bd, bs)


def _validate_fast_move(entry: Mapping[str, Any]) -> FastMoveRow:
    try:
        name = str(entry["name"]).strip()
        dmg = float(entry["damage"])  # noqa: N806
        e_gain = float(entry["energy_gain"])  # noqa: N806
        turns = int(entry["turns"])  # noqa: N806
        availability = str(entry.get("availability", "standard")).strip() or "standard"
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Fast move missing or invalid fields: name/damage/energy_gain/turns") from exc
    if not name:
        raise ValueError("Fast move name cannot be empty")
    if dmg < 0 or e_gain <= 0 or turns <= 0:
        raise ValueError("Fast move damage>=0, energy_gain>0, turns>0 required")
    return FastMoveRow(name, dmg, e_gain, turns, availability)


def _validate_charge_move(entry: Mapping[str, Any]) -> ChargeMoveRow:
    try:
        name = str(entry["name"]).strip()
        dmg = float(entry["damage"])  # noqa: N806
        e_cost = float(entry["energy_cost"])  # noqa: N806
        reliability = entry.get("reliability")
        reliability_value = float(reliability) if reliability is not None else None
        has_buff = bool(entry.get("has_buff", False))
        availability = str(entry.get("availability", "standard")).strip() or "standard"
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Charge move missing or invalid fields: name/damage/energy_cost") from exc
    if not name:
        raise ValueError("Charge move name cannot be empty")
    if dmg < 0 or e_cost <= 0:
        raise ValueError("Charge move damage>=0, energy_cost>0 required")
    return ChargeMoveRow(name, dmg, e_cost, reliability_value, has_buff, availability)


def _normalise_species(payload: Any) -> list[SpeciesRow]:
    if isinstance(payload, Mapping) and "species" in payload:
        raw = payload["species"]
    else:
        raw = payload
    if not isinstance(raw, Sequence):
        raise ValueError("Species JSON must be a list or an object with 'species' list")
    return [_validate_species_entry(entry) for entry in raw]


def _normalise_moves(payload: Any) -> tuple[list[FastMoveRow], list[ChargeMoveRow]]:
    if not isinstance(payload, Mapping):
        raise ValueError("Moves JSON must be an object with 'fast' and 'charge' lists")
    fast_raw = payload.get("fast", [])
    charge_raw = payload.get("charge", [])
    if not isinstance(fast_raw, Sequence) or not isinstance(charge_raw, Sequence):
        raise ValueError("Moves JSON must contain 'fast' and 'charge' lists")
    fast = [_validate_fast_move(entry) for entry in fast_raw]
    charge = [_validate_charge_move(entry) for entry in charge_raw]
    return fast, charge


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--species-in", required=True, type=Path, help="Path to species JSON input.")
    parser.add_argument("--moves-in", required=True, type=Path, help="Path to moves JSON input.")
    parser.add_argument("--out-dir", type=Path, help="Output directory for normalized JSON files.")
    parser.add_argument("--prefix", help="Prefix for output filenames (default: normalized)")
    parser.add_argument("--source-tag", help="Optional short source tag to include in metadata.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> tuple[Path, Path]:
    args = parse_args(argv)
    species_payload = _load_json(args.species_in)
    moves_payload = _load_json(args.moves_in)

    species = _normalise_species(species_payload)
    fast, charge = _normalise_moves(moves_payload)

    now = datetime.now(timezone.utc).isoformat()
    prefix = (args.prefix or "normalized").rstrip("_")
    out_dir = args.out_dir or Path("normalized_data")
    species_out = out_dir / f"{prefix}_species.json"
    moves_out = out_dir / f"{prefix}_moves.json"

    shared_meta = {
        "source": args.source_tag or "local",
        "generated_at": now,
        "counts": {"species": len(species), "fast_moves": len(fast), "charge_moves": len(charge)},
    }

    _write_json(
        species_out,
        {
            "metadata": shared_meta,
            "species": [
                {
                    "name": row.name,
                    "base_attack": row.base_attack,
                    "base_defense": row.base_defense,
                    "base_stamina": row.base_stamina,
                }
                for row in species
            ],
        },
    )
    _write_json(
        moves_out,
        {
            "metadata": shared_meta,
            "fast": [
                {
                    "name": row.name,
                    "damage": row.damage,
                    "energy_gain": row.energy_gain,
                    "turns": row.turns,
                    "availability": row.availability,
                }
                for row in fast
            ],
            "charge": [
                {
                    "name": row.name,
                    "damage": row.damage,
                    "energy_cost": row.energy_cost,
                    "reliability": row.reliability,
                    "has_buff": row.has_buff,
                    "availability": row.availability,
                }
                for row in charge
            ],
        },
    )

    print("Saved:", species_out.resolve())
    print("Saved:", moves_out.resolve())
    return species_out, moves_out


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()

