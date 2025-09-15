"""Command line interface for Pokémon analysis."""
from __future__ import annotations

import argparse
import json
from typing import Tuple

from . import data_loader, social
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

    leaderboard_parser = subparsers.add_parser(
        "leaderboard", help="View or submit stored raid scores"
    )
    leaderboard_parser.add_argument(
        "--login", metavar="USERNAME", help="Authenticate for storing scores"
    )
    leaderboard_parser.add_argument(
        "--logout", action="store_true", help="Clear the saved login session"
    )
    leaderboard_parser.add_argument(
        "--submit", type=float, metavar="SCORE", help="Submit a score to the leaderboard"
    )
    leaderboard_parser.add_argument(
        "--label", help="Optional label describing the score entry"
    )
    leaderboard_parser.add_argument(
        "--details", help="Additional context to store with the score"
    )
    leaderboard_parser.add_argument(
        "--output", choices=["text", "json"], default="text"
    )

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

    if args.command == "leaderboard":
        if args.logout:
            social.logout()
            print("Cleared saved login session.")
        logged_in = None
        if args.login:
            try:
                logged_in = social.login(args.login)
            except ValueError as exc:
                parser.error(str(exc))
            print(f"Logged in as {logged_in}.")
        if args.submit is not None:
            try:
                entry = social.record_score(
                    args.submit,
                    label=args.label,
                    details=args.details,
                )
            except ValueError as exc:
                parser.error(str(exc))
            if args.output == "json":
                print(json.dumps(entry, indent=2))
            else:
                label_text = f" [{entry['label']}]" if entry.get("label") else ""
                detail_text = f" – {entry['details']}" if entry.get("details") else ""
                print(
                    f"Recorded {entry['score']:.2f} for {entry['user']}{label_text}{detail_text}"
                )
            return
        leaderboard = social.load_leaderboard()
        if args.output == "json":
            print(json.dumps(leaderboard, indent=2))
        else:
            if not leaderboard:
                print("Leaderboard is empty.")
            else:
                for idx, entry in enumerate(leaderboard, 1):
                    label_text = f" [{entry['label']}]" if entry.get("label") else ""
                    detail_text = f" – {entry['details']}" if entry.get("details") else ""
                    print(
                        f"{idx}. {entry['user']} – {entry['score']:.2f}{label_text}{detail_text}"
                    )
            active_user = social.get_current_user()
            if active_user:
                print(f"Logged in as: {active_user}")
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
        event_modifiers = result.get("event_modifiers", {})
        active_events = event_modifiers.get("active_events", [])
        if active_events:
            print("Active modifiers: " + ", ".join(active_events))

        move_override = (
            event_modifiers.get("moves", {})
            .get(result["name"], {})
            .get(result["form"])
        )
        if move_override:
            fast_moves = ", ".join(move_override.get("fast", [])) or "—"
            charged_moves = ", ".join(move_override.get("charged", [])) or "—"
            event_name = move_override.get("event")
            if event_name:
                print(
                    f"Moves adjusted by {event_name}: fast {fast_moves}; "
                    f"charged {charged_moves}"
                )
            else:
                print(
                    f"Moves adjusted for event: fast {fast_moves}; "
                    f"charged {charged_moves}"
                )

        cp_overrides = event_modifiers.get("cp_caps", {})
        for league, data in result["pvp"].items():
            line = (
                f"{league.title()} League: level {data['level']}, CP {data['cp']}, "
                f"XL required: {data['requires_xl']}"
            )
            override = cp_overrides.get(league)
            if isinstance(override, dict) and override.get("value") is not None:
                line += f" [Event cap {override['value']}"
                if override.get("event"):
                    line += f" ({override['event']})"
                line += "]"
            elif override:
                line += f" [Event cap {override}]"
            print(line)


if __name__ == "__main__":  # pragma: no cover
    main()
