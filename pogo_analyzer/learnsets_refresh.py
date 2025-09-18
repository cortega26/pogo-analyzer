"""Offline learnsets normaliser.

Accepts a simple CSV/JSON map of species to allowed PvP moves and emits the
learnsets JSON consumed by the PvP scoreboard tool. Validates that referenced
moves exist in the normalized moves file.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON from {path}: {exc}") from exc


def _load_map_csv(path: Path) -> dict[str, dict[str, list[str]]]:
    mapping: dict[str, dict[str, list[str]]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"species", "fast", "charge"}
        missing = required - set(h.lower() for h in (reader.fieldnames or []))
        if missing:
            raise ValueError(f"CSV is missing required columns: {sorted(missing)}")
        fidx = [h for h in (reader.fieldnames or []) if h.lower() == "fast"][0]
        cidx = [h for h in (reader.fieldnames or []) if h.lower() == "charge"][0]
        sidx = [h for h in (reader.fieldnames or []) if h.lower() == "species"][0]
        for row in reader:
            name = (row.get(sidx) or "").strip()
            if not name:
                continue
            fast = [m.strip() for m in (row.get(fidx) or "").replace("|", ";").split(";") if m.strip()]
            charge = [m.strip() for m in (row.get(cidx) or "").replace("|", ";").split(";") if m.strip()]
            mapping[name] = {"fast": fast, "charge": charge}
    return mapping


def _validate(mapping: Mapping[str, Mapping[str, list[str]]], moves_payload: Mapping[str, Any]) -> None:
    fast_names = {str(r["name"]) for r in moves_payload.get("fast", [])}
    charge_names = {str(r["name"]) for r in moves_payload.get("charge", [])}
    for species, moves in mapping.items():
        for m in moves.get("fast", []):
            if m not in fast_names:
                raise ValueError(f"Unknown fast move for {species!r}: {m!r}")
        for m in moves.get("charge", []):
            if m not in charge_names:
                raise ValueError(f"Unknown charge move for {species!r}: {m!r}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--moves-in", required=True, type=Path, help="Normalized moves JSON from pogo-data-refresh.")
    p.add_argument("--map-in", required=True, type=Path, help="Species→moves mapping (CSV or JSON).")
    p.add_argument("--out", required=True, type=Path, help="Output learnsets JSON path.")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> Path:
    args = parse_args(argv)
    moves_payload = _load_json(args.moves_in)
    if args.map_in.suffix.lower() == ".csv":
        mapping = _load_map_csv(args.map_in)
    else:
        raw = _load_json(args.map_in)
        if not isinstance(raw, Mapping):
            raise ValueError("JSON learnset map must be an object: {species: {fast:[], charge:[]}}")
        mapping = {str(k): {"fast": list(v.get("fast", [])), "charge": list(v.get("charge", []))} for k, v in raw.items()}

    _validate(mapping, moves_payload)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Saved:", args.out.resolve())
    return args.out


if __name__ == "__main__":  # pragma: no cover
    main()

