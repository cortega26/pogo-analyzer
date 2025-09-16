"""Command line interface for Pokémon analysis."""
from __future__ import annotations

import argparse
import json
from typing import Sequence, Tuple, cast

from . import data_loader, social
from .analysis import analyze_pokemon
from .errors import PogoAnalyzerError
from .observability import configure_logging, generate_trace_id, get_logger
from .team_builder import Roster


def parse_iv(values: Sequence[str]) -> Tuple[int, int, int]:
    if len(values) != 3:
        raise argparse.ArgumentTypeError("IV requires three integers")
    converted = [int(part) for part in values]
    return converted[0], converted[1], converted[2]


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
    configure_logging()
    logger = get_logger(__name__)
    parser = build_parser()
    args = parser.parse_args()
    trace_id = generate_trace_id()

    try:
        if args.command == "team":
            roster = Roster.load()
            if args.team_command == "create":
                try:
                    roster.create_team(args.name)
                except ValueError as exc:
                    logger.warning(
                        "team_create_failed",
                        extra={
                            "event": "team_create_failed",
                            "trace_id": trace_id,
                            "team_name": args.name,
                        },
                    )
                    parser.error(str(exc))
                logger.info(
                    "team_created",
                    extra={"event": "team_created", "trace_id": trace_id, "team_name": args.name},
                )
                print(f"Created team '{args.name}'.")
                return
            if args.team_command == "add":
                ivs = parse_iv(cast(Sequence[str], args.iv))
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
                    logger.warning(
                        "team_add_failed",
                        extra={
                            "event": "team_add_failed",
                            "trace_id": trace_id,
                            "team_name": args.name,
                        },
                    )
                    parser.error(str(exc))
                logger.info(
                    "team_member_added",
                    extra={"event": "team_member_added", "trace_id": trace_id, "team_name": args.name},
                )
                print(f"Added {args.species} to team '{args.name}'.")
                return
            if args.team_command == "recommend":
                try:
                    recommendation = roster.recommend(args.name, args.league)
                except (ValueError, KeyError) as exc:
                    logger.warning(
                        "team_recommend_failed",
                        extra={
                            "event": "team_recommend_failed",
                            "trace_id": trace_id,
                            "team_name": args.name,
                            "league": args.league,
                        },
                    )
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
                logger.info(
                    "team_recommend_completed",
                    extra={
                        "event": "team_recommend_completed",
                        "trace_id": trace_id,
                        "team_name": args.name,
                        "league": args.league,
                    },
                )
                return

        if args.command == "leaderboard":
            if args.logout:
                social.logout()
                logger.info(
                    "leaderboard_logout",
                    extra={"event": "leaderboard_logout", "trace_id": trace_id},
                )
                print("Cleared saved login session.")
            logged_in = None
            if args.login:
                try:
                    logged_in = social.login(args.login)
                except ValueError as exc:
                    logger.warning(
                        "leaderboard_login_failed",
                        extra={"event": "leaderboard_login_failed", "trace_id": trace_id},
                    )
                    parser.error(str(exc))
                logger.info(
                    "leaderboard_login",
                    extra={"event": "leaderboard_login", "trace_id": trace_id},
                )
                print(f"Logged in as {logged_in}.")
            if args.submit is not None:
                try:
                    entry = social.record_score(
                        args.submit,
                        label=args.label,
                        details=args.details,
                    )
                except ValueError as exc:
                    logger.warning(
                        "leaderboard_submit_failed",
                        extra={"event": "leaderboard_submit_failed", "trace_id": trace_id},
                    )
                    parser.error(str(exc))
                if args.output == "json":
                    print(json.dumps(entry, indent=2))
                else:
                    label_text = f" [{entry['label']}]" if entry.get("label") else ""
                    detail_text = f" – {entry['details']}" if entry.get("details") else ""
                    print(
                        f"Recorded {entry['score']:.2f} for {entry['user']}{label_text}{detail_text}"
                    )
                logger.info(
                    "leaderboard_submit",
                    extra={"event": "leaderboard_submit", "trace_id": trace_id},
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
            logger.info(
                "leaderboard_list",
                extra={"event": "leaderboard_list", "trace_id": trace_id, "entries": len(leaderboard)},
            )
            return

        if args.screenshot:
            from .vision import scan_screenshot

            scanned = scan_screenshot(args.screenshot)
            species = args.species or cast(str, scanned["name"])
            form = args.form or cast(str, scanned["form"])
            ivs = (
                parse_iv(cast(Sequence[str], args.iv))
                if args.iv
                else cast(Tuple[int, int, int], scanned["ivs"])
            )
            level = args.level if args.level is not None else cast(float, scanned["level"])
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
            ivs = parse_iv(cast(Sequence[str], args.iv))
            level = args.level if args.level is not None else 1.0

        result = analyze_pokemon(
            cast(str, species),
            cast(str, form),
            cast(Tuple[int, int, int], ivs),
            cast(float, level),
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

        logger.info(
            "cli_command_completed",
            extra={"event": "cli_command_completed", "trace_id": trace_id},
        )
    except PogoAnalyzerError as exc:
        logger.error(
            "cli_command_failed",
            extra={"event": "cli_command_failed", "trace_id": trace_id, "error": exc.to_payload()},
        )
        parser.error(f"{exc.message} (trace: {trace_id})")
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception(
            "cli_unhandled_error",
            extra={"event": "cli_unhandled_error", "trace_id": trace_id},
        )
        parser.error(f"Unexpected error: {exc}. Reference trace {trace_id}.")


if __name__ == "__main__":  # pragma: no cover
    main()
