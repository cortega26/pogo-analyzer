"""Command line interface for Pokémon analysis."""
from __future__ import annotations

import argparse
import json
from typing import Tuple

from .analysis import analyze_pokemon


def parse_iv(string_list) -> Tuple[int, int, int]:
    if len(string_list) != 3:
        raise argparse.ArgumentTypeError("IV requires three integers")
    return tuple(int(x) for x in string_list)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a single Pokémon")
    parser.add_argument("--species")
    parser.add_argument("--form")
    parser.add_argument("--iv", nargs=3, metavar=("ATK", "DEF", "STA"))
    parser.add_argument("--level", type=float)
    parser.add_argument("--screenshot", help="Path to a screenshot to scan for stats")
    parser.add_argument("--shadow", action="store_true")
    parser.add_argument("--purified", action="store_true")
    parser.add_argument("--best-buddy", action="store_true", dest="best_buddy")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.screenshot:
        from .vision import scan_screenshot

        scanned = scan_screenshot(args.screenshot)
        species = args.species or scanned["name"]
        form = args.form or scanned["form"]
        ivs = parse_iv(args.iv) if args.iv else scanned["ivs"]
        level = args.level if args.level is not None else scanned["level"]
        if species is None:
            parser.error("Unable to determine species from screenshot; please specify --species")
        if ivs is None:
            parser.error("Unable to determine IVs from screenshot; please provide --iv")
        if level is None:
            parser.error("Unable to determine level from screenshot; please provide --level")
    else:
        if not args.species:
            parser.error("--species is required when --screenshot is not provided")
        if not args.iv:
            parser.error("--iv is required when --screenshot is not provided")
        species = args.species
        form = args.form or "Normal"
        ivs = parse_iv(args.iv)
        level = args.level if args.level is not None else 1.0

    result = analyze_pokemon(
        species,
        form,
        ivs,
        level,
        shadow=args.shadow,
        purified=args.purified,
        best_buddy=args.best_buddy,
    )

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['name']} ({result['form']}) - CP {result['cp']}")
        for league, data in result["pvp"].items():
            print(
                f"{league.title()} League: level {data['level']}, CP {data['cp']}, "
                f"XL required: {data['requires_xl']}"
            )


if __name__ == "__main__":  # pragma: no cover
    main()
