"""Command line interface for Pokémon analysis."""
from __future__ import annotations

import argparse
import json
from typing import Tuple

from . import data_loader
from .analysis import analyze_pokemon
from .team_builder import Roster


def parse_iv(string_list) -> Tuple[int, int, int]:
    if len(string_list) != 3:
        raise argparse.ArgumentTypeError("IV requires three integers")
    return tuple(int(x) for x in string_list)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze a single Pokémon or manage saved teams"
    )
    parser.add_argument("--species")
    parser.add_argument("--form")
    parser.add_argument("--iv", nargs=3, metavar=("ATK", "DEF", "STA"))
    parser.add_argument("--level", type=float)
    parser.add_argument("--screenshot", help="Path to a screenshot to scan for stats")
    parser.add_argument("--shadow", action="store_true")
    parser.add_argument("--purified", action="store_true")
    parser.add_argument("--best-buddy", action="store_true", dest="best_buddy")
    parser.add_argument("--output", choices=["text", "json"], default="text")

    subparsers = parser.add_subparsers(dest="command")

    team_parser = subparsers.add_parser("team", help="Manage saved teams")
    team_subparsers = team_parser.add_subparsers(dest="team_command", required=True)

    create_parser = team_subparsers.add_parser("create", help="Create a new team")
    create_parser.add_argument("name")

    add_parser = team_subparsers.add_parser("add", help="Add a Pokémon to a team")
    add_parser.add_argument("name", help="Team name")
    add_parser.add_argument("--species", required=True)
    add_parser.add_argument("--form", default="Normal")
    add_parser.add_argument("--iv", nargs=3, metavar=("ATK", "DEF", "STA"), required=True)
    add_parser.add_argument("--level", type=float, required=True)
    add_parser.add_argument("--shadow", action="store_true")
    add_parser.add_argument("--purified", action="store_true")
    add_parser.add_argument("--best-buddy", action="store_true", dest="best_buddy")

    recommend_parser = team_subparsers.add_parser(
        "recommend", help="Recommend the best team member for a given league"
    )
    recommend_parser.add_argument("name", help="Team name")
    recommend_parser.add_argument(
        "--league",
        choices=sorted(data_loader.LEAGUE_CP_CAPS),
        default="great",
    )
    recommend_parser.add_argument("--output", choices=["text", "json"], default="text")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "team":
        roster = Roster.load()
        if args.team_command == "create":
            try:
                roster.create_team(args.name)
            except ValueError as exc:
                parser.error(str(exc))
            print(f"Created team '{args.name}'.")
            return
        if args.team_command == "add":
            ivs = parse_iv(args.iv)
            try:
                roster.add_member(
                    args.name,
                    species=args.species,
                    form=args.form,
                    ivs=ivs,
                    level=args.level,
                    shadow=args.shadow,
                    purified=args.purified,
                    best_buddy=args.best_buddy,
                )
            except (ValueError, KeyError) as exc:
                parser.error(str(exc))
            print(f"Added {args.species} to team '{args.name}'.")
            return
        if args.team_command == "recommend":
            try:
                recommendation = roster.recommend(args.name, args.league)
            except (ValueError, KeyError) as exc:
                parser.error(str(exc))
            if args.output == "json":
                print(json.dumps(recommendation, indent=2))
            else:
                best = recommendation["analysis"]
                league_data = best["pvp"][args.league]
                print(
                    f"Best for {args.league.title()} League: {best['name']} ({best['form']})"
                )
                print(
                    f"Level {league_data['level']} CP {league_data['cp']} - "
                    f"stat product {league_data['stat_product']:.0f}"
                )
            return

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
