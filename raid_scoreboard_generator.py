"""
Generate a ranked raid scoreboard from curated Pokémon entries.

The script mirrors the heuristics used in the original spreadsheet-based
workflow and produces the same set of columns regardless of whether pandas is
installed. Invoke :func:`main` directly or import the helper functions into your
own scripts for more control over data filtering and presentation.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from pogo_analyzer import scoreboard as _scoreboard
from pogo_analyzer.data import PokemonRaidEntry
from pogo_analyzer.data.move_guidance import get_move_guidance, normalise_name
from pogo_analyzer.scoreboard import (
    RAID_ENTRIES,
    ExportResult,
    Row,
    ScoreboardExportConfig,
    SimpleTable,
    TableLike,
    calculate_iv_bonus,
    calculate_raid_score,
    iv_bonus,
    raid_score,
    score,
)
from pogo_analyzer.scoreboard import (
    add_priority_tier as _scoreboard_add_priority_tier,
)
from pogo_analyzer.scoreboard import (
    build_dataframe as _scoreboard_build_dataframe,
)
from pogo_analyzer.scoreboard import (
    build_entry_rows as _scoreboard_build_entry_rows,
)
from pogo_analyzer.scoreboard import (
    build_export_config as _scoreboard_build_export_config,
)
from pogo_analyzer.scoreboard import (
    build_rows as _scoreboard_build_rows,
)
from pogo_analyzer.scoreboard import (
    generate_scoreboard as _scoreboard_generate_scoreboard,
)
from pogo_analyzer.scoring.metrics import SCORE_MAX, SCORE_MIN

pd: ModuleType | None = None
try:  # Pandas provides richer output; fall back to a lightweight table otherwise.
    import pandas as _pd
except ModuleNotFoundError:  # pragma: no cover - exercised when pandas is absent.
    pd = None
else:
    pd = _pd

# Re-export data helpers for compatibility with historical imports.
build_entry_rows = _scoreboard_build_entry_rows
build_rows = _scoreboard_build_rows


def _sync_pandas() -> None:
    """Mirror the current pandas availability into the shared scoreboard module."""

    _scoreboard.pd = pd


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Return parsed command-line arguments for :func:`main`."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory where CSV/Excel files should be written.",
    )
    parser.add_argument(
        "--csv-name",
        help="File name (or path) for the CSV export. Defaults to raid_scoreboard.csv.",
    )
    parser.add_argument(
        "--excel-name",
        help="File name (or path) for the Excel export. Defaults to raid_scoreboard.xlsx.",
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="Disable Excel export even when pandas is available.",
    )
    parser.add_argument(
        "--preview-limit",
        type=int,
        help="Number of rows to include in the console preview (default: 10).",
    )
    parser.add_argument(
        "--pokemon-name",
        help="Evaluate a single Pokémon and print a recommendation instead of exporting files.",
    )
    parser.add_argument(
        "--combat-power", type=int, help="Combat Power displayed in-game."
    )
    parser.add_argument(
        "--ivs",
        type=int,
        nargs=3,
        metavar=("ATK", "DEF", "STA"),
        help="Individual values in Attack/Defence/Stamina order.",
    )
    parser.add_argument(
        "--shadow", action="store_true", help="Mark the Pokémon as a shadow variant."
    )
    parser.add_argument(
        "--purified", action="store_true", help="Mark the Pokémon as purified."
    )
    parser.add_argument(
        "--lucky", action="store_true", help="Apply the lucky trade bonus."
    )
    parser.add_argument(
        "--best-buddy", action="store_true", help="Apply the best buddy bonus."
    )
    parser.add_argument(
        "--needs-tm",
        action="store_true",
        help="Indicate that an Elite TM or special move is required.",
    )
    parser.add_argument(
        "--has-special-move",
        action="store_true",
        help="Set when the exclusive move is already unlocked.",
    )
    parser.add_argument(
        "--final-form", help="Override the final evolution name used in the report."
    )
    parser.add_argument("--role", help="Short description of the Pokémon's raid role.")
    parser.add_argument(
        "--notes", help="Additional context to display in the recommendation."
    )
    return parser.parse_args(argv)


def build_export_config(
    args: argparse.Namespace,
    env: Mapping[str, str] | None = None,
) -> ScoreboardExportConfig:
    """Proxy to :func:`pogo_analyzer.scoreboard.build_export_config`."""

    return _scoreboard_build_export_config(args, env=env)


def build_dataframe(
    entries: Sequence[PokemonRaidEntry] = RAID_ENTRIES,
) -> TableLike:
    """Construct a table using the shared scoreboard helpers with the current pandas state."""

    _sync_pandas()
    return _scoreboard_build_dataframe(entries)


def add_priority_tier(df: TableLike) -> TableLike:
    """Append priority tiers via the shared scoreboard helper."""

    return _scoreboard_add_priority_tier(df)


def _priority_label(score: float) -> str:
    """Return the qualitative tier used in the scoreboard."""

    if score >= 90:
        return "S (Build ASAP)"
    if score >= 85:
        return "A (High)"
    if score >= 78:
        return "B (Good)"
    if score >= 70:
        return "C (Situational)"
    return "D (Doesn't belong on a Raids list)"


def _score_from_combat_power(combat_power: int) -> float:
    """Normalise combat power into the 1–100 raid score baseline."""

    scaled = (combat_power - 2000) / 100 + 70
    return max(SCORE_MIN, min(SCORE_MAX, round(scaled, 1)))


def _cp_penalty(combat_power: int | None) -> float:
    """Return a penalty for underpowered Pokémon based on combat power."""

    if combat_power is None:
        return 0.0
    target = 3100
    if combat_power >= target:
        return 0.0
    penalty = (target - combat_power) / 350
    return max(0.0, min(20.0, round(penalty, 1)))


@dataclass(frozen=True)
class TemplateLookup:
    """Describe how a template lookup resolved for a given Pokémon name."""

    entry: PokemonRaidEntry | None
    name_matches: bool


def _template_entry(
    name: str,
    *,
    shadow: bool,
    purified: bool,
    best_buddy: bool,
) -> TemplateLookup:
    """Return the best matching entry or metadata about why it is missing."""

    key = normalise_name(name)
    matches = [entry for entry in RAID_ENTRIES if normalise_name(entry.name) == key]
    if not matches:
        return TemplateLookup(entry=None, name_matches=False)

    same_shadow = [entry for entry in matches if entry.shadow == shadow]
    if not same_shadow:
        return TemplateLookup(entry=None, name_matches=True)

    candidates = same_shadow
    same_purified = [entry for entry in candidates if entry.purified == purified]
    if same_purified:
        candidates = same_purified
    same_best_buddy = [entry for entry in candidates if entry.best_buddy == best_buddy]
    if same_best_buddy:
        candidates = same_best_buddy

    return TemplateLookup(entry=max(candidates, key=lambda entry: entry.base), name_matches=True)


def _evaluate_single_pokemon(args: argparse.Namespace) -> None:
    """Print a recommendation for a single Pokémon supplied via CLI."""

    if args.combat_power is None or args.pokemon_name is None or args.ivs is None:
        raise SystemExit(
            "--pokemon-name, --combat-power, and --ivs must be provided to evaluate a single Pokémon."
        )

    ivs = tuple(args.ivs)
    lookup = _template_entry(
        args.pokemon_name,
        shadow=args.shadow,
        purified=args.purified,
        best_buddy=args.best_buddy,
    )
    template = lookup.entry
    if args.pokemon_name and (template or not lookup.name_matches):
        guidance = get_move_guidance(args.pokemon_name)
    else:
        guidance = None

    if template:
        base_score = template.base
        role = args.role or template.role
        final_form = args.final_form or template.final_form
    else:
        base_score = _score_from_combat_power(args.combat_power)
        role = args.role or ""
        final_form = args.final_form or ""

    base_score = max(SCORE_MIN, min(SCORE_MAX, base_score))
    penalty = _cp_penalty(args.combat_power if template else None)

    template_requires_move = template.requires_special_move if template else False
    template_missing_move = template.needs_tm if template else False
    guidance_requires_move = guidance.needs_tm if guidance else False
    requires_special_move = bool(
        template_requires_move or guidance_requires_move or args.needs_tm
    )

    if args.has_special_move:
        needs_tm = False
    elif args.needs_tm:
        needs_tm = True
    elif template_missing_move:
        needs_tm = True
    elif requires_special_move:
        needs_tm = True
    else:
        needs_tm = False

    note_parts: list[str] = []
    if args.notes:
        note_parts.append(args.notes)
    if template and template.notes:
        if not (args.has_special_move and template_requires_move):
            note_parts.append(template.notes)
    if guidance and guidance.note and not args.has_special_move:
        note_parts.append(guidance.note)

    notes = " ".join(dict.fromkeys(part for part in note_parts if part)).strip()
    if penalty > 0:
        cp_note = "Power up this Pokémon; current CP is below raid-ready levels."
        if cp_note not in notes:
            notes = f"{notes} {cp_note}".strip()

    entry = PokemonRaidEntry(
        args.pokemon_name,
        ivs,
        final_form=final_form,
        role=role,
        base=base_score,
        lucky=args.lucky,
        shadow=args.shadow,
        requires_special_move=requires_special_move,
        needs_tm=needs_tm,
        notes=notes,
        purified=args.purified,
        best_buddy=args.best_buddy,
    )

    row = entry.to_row()
    score = row["Raid Score (1-100)"]
    tier = _priority_label(score)

    status_bits: list[str] = []
    if args.shadow:
        status_bits.append("Shadow")
    if args.purified:
        status_bits.append("Purified")
    if args.lucky:
        status_bits.append("Lucky")
    if args.best_buddy:
        status_bits.append("Best Buddy")
    if penalty > 0:
        status_bits.append("Underpowered")
    if needs_tm:
        status_bits.append("Exclusive move missing")

    print("Single Pokémon evaluation")
    print("-------------------------")
    print(f"Name: {entry.formatted_name()}")
    print(f"Combat Power: {args.combat_power}")
    print(f"IVs: {ivs[0]}/{ivs[1]}/{ivs[2]}")
    if guidance and guidance.required_move:
        print(f"Recommended Charged Move: {guidance.required_move}")
    if needs_tm:
        action_note = None
        if guidance and guidance.note and not args.has_special_move:
            action_note = guidance.note
        elif template and template.notes and not args.has_special_move:
            action_note = template.notes
        elif args.notes:
            action_note = args.notes
        if action_note:
            print(f"Action: {action_note}")
    if args.has_special_move and (guidance or template) and needs_tm is False:
        print("Exclusive move already unlocked.")
    if penalty > 0:
        print(
            "Power Recommendation: Power up this Pokémon; current CP is below raid-ready levels."
        )
    if status_bits:
        print("Status: " + ", ".join(status_bits))
    print(f"Raid Score: {score}/100")
    print(f"Priority Tier: {tier}")
    note = row.get("Why it scores like this")
    if note:
        print("Notes: " + note)


def generate_scoreboard(
    entries: Sequence[PokemonRaidEntry] = RAID_ENTRIES,
    *,
    config: ScoreboardExportConfig,
) -> ExportResult:
    """Build, rank, and persist the raid scoreboard using the shared helpers."""

    _sync_pandas()
    return _scoreboard_generate_scoreboard(entries, config=config)


def main(argv: Sequence[str] | None = None) -> ExportResult | None:
    """Command-line entry point for generating raid scoreboard exports."""

    args = parse_args(argv)
    if args.pokemon_name:
        _evaluate_single_pokemon(args)
        return None

    try:
        config = build_export_config(args)
    except ValueError as exc:  # pragma: no cover - handled via CLI exit code.
        raise SystemExit(str(exc)) from exc

    result = generate_scoreboard(RAID_ENTRIES, config=config)

    print("Saved:", result.csv_path.resolve())
    if result.excel_path is None:
        print("Skipped Excel export: disabled via configuration.")
    elif result.excel_written:
        print("Saved:", result.excel_path.resolve())
    else:
        if result.excel_error == "pandas-missing":
            print("Skipped Excel export: install pandas to enable Excel output.")
        else:
            reason = result.excel_error or "unknown error"
            lower_reason = reason.lower()
            suggestion = ""
            if "openpyxl" in lower_reason:
                suggestion = " (install openpyxl)"
            elif "xlsxwriter" in lower_reason:
                suggestion = " (install xlsxwriter)"
            print(f"Warning: failed to write Excel{suggestion}. Reason:", reason)

    preview_limit = config.preview_limit
    print()
    print(f"Top {preview_limit} preview:")
    print(result.table.head(preview_limit).to_string(index=False))

    return result


__all__ = [
    "RAID_ENTRIES",
    "PokemonRaidEntry",
    "TableLike",
    "Row",
    "SimpleTable",
    "ScoreboardExportConfig",
    "ExportResult",
    "build_entry_rows",
    "build_rows",
    "add_priority_tier",
    "build_dataframe",
    "build_export_config",
    "generate_scoreboard",
    "parse_args",
    "calculate_iv_bonus",
    "calculate_raid_score",
    "iv_bonus",
    "raid_score",
    "score",
    "main",
]

if __name__ == "__main__":
    main()
