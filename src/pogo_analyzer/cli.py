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
    parser.add_argument("--species", required=True)
    parser.add_argument("--form", default="Normal")
    parser.add_argument("--iv", nargs=3, metavar=("ATK", "DEF", "STA"), required=True)
    parser.add_argument("--level", type=float, default=1.0)
    parser.add_argument("--shadow", action="store_true")
    parser.add_argument("--purified", action="store_true")
    parser.add_argument("--best-buddy", action="store_true", dest="best_buddy")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    args = parser.parse_args()

    ivs = parse_iv(args.iv)
    result = analyze_pokemon(
        args.species,
        args.form,
        ivs,
        args.level,
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
