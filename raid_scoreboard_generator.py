"""
Generate a ranked raid scoreboard from curated Pokémon entries.

The script mirrors the heuristics used in the original spreadsheet-based
workflow and produces the same set of columns regardless of whether pandas is
installed. Invoke :func:`main` directly or import the helper functions into your
own scripts for more control over data filtering and presentation.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from pogo_analyzer import scoreboard as _scoreboard
from pogo_analyzer.data import PokemonRaidEntry
from pogo_analyzer.data.base_stats import BaseStats, load_default_base_stats
from pogo_analyzer.data.move_guidance import get_move_guidance, normalise_name
from pogo_analyzer.formulas import effective_stats, infer_level_from_cp
from pogo_analyzer.pve import ChargeMove, FastMove, compute_pve_score
from pogo_analyzer.pvp import (
    DEFAULT_LEAGUE_CONFIGS,
    PvpChargeMove,
    PvpFastMove,
    compute_pvp_score,
)
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
        "--combat-power",
        "--cp",
        dest="combat_power",
        type=int,
        help="Combat Power displayed in-game (alias: --cp).",
    )
    parser.add_argument(
        "--target-cp",
        type=int,
        help="Target combat power for a fully powered build (use to evaluate underpowered status).",
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
        "--best-buddy",
        "--bb",
        dest="best_buddy",
        action="store_true",
        help="Apply the best buddy bonus (alias: --bb).",
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

    inference_group = parser.add_argument_group("Level inference")
    inference_group.add_argument(
        "--species",
        help="Species name used for level/stat inference (defaults to --pokemon-name).",
    )
    inference_group.add_argument(
        "--base-stats",
        type=int,
        nargs=3,
        metavar=("BASE_ATK", "BASE_DEF", "BASE_STA"),
        help=(
            "Base stats for the species in Attack/Defence/Stamina order. "
            "Defaults to an automatic lookup when omitted."
        ),
    )
    inference_group.add_argument(
        "--observed-hp",
        type=int,
        help="Observed HP to disambiguate CP collisions when inferring level.",
    )

    pve_group = parser.add_argument_group("PvE scoring")
    pve_group.add_argument(
        "--fast",
        dest="fast_move",
        metavar="MOVE",
        help=(
            "Fast move descriptor: name,power,energy_gain,duration"
            "[,stab=...][,weather=...][,type=...][,turns=...]"
        ),
    )
    pve_group.add_argument(
        "--charge",
        dest="charge_moves",
        action="append",
        metavar="MOVE",
        help=(
            "Charge move descriptor: name,power,energy_cost,duration"
            "[,stab=...][,weather=...][,type=...][,reliability=...][,buff=...]"
        ),
    )
    pve_group.add_argument(
        "--weather",
        dest="weather_boost",
        action="store_true",
        help="Apply weather boost to all moves unless overridden per move.",
    )
    pve_group.add_argument(
        "--target-defense",
        dest="target_defense",
        type=float,
        help="Target defence value used for PvE EHP estimation.",
    )
    pve_group.add_argument(
        "--incoming-dps",
        dest="incoming_dps",
        type=float,
        help="Incoming DPS from the raid boss used for PvE TDO calculations.",
    )
    pve_group.add_argument(
        "--alpha",
        dest="alpha",
        type=float,
        help="Blend factor between DPS and TDO in the PvE value formula (default: 0.6).",
    )

    pvp_group = parser.add_argument_group("PvP scoring")
    pvp_group.add_argument(
        "--league-cap",
        dest="league_cap",
        type=int,
        help="CP cap for the PvP league (1500, 2500, or omit for default Great League).",
    )
    pvp_group.add_argument(
        "--beta",
        dest="beta",
        type=float,
        help="Blend factor between stat product and move pressure (default: 0.52).",
    )
    pvp_group.add_argument(
        "--sp-ref",
        dest="stat_product_reference",
        type=float,
        help="Reference stat product used for PvP normalisation.",
    )
    pvp_group.add_argument(
        "--mp-ref",
        dest="move_pressure_reference",
        type=float,
        help="Reference move pressure used for PvP normalisation.",
    )
    pvp_group.add_argument(
        "--bait-prob",
        dest="bait_probability",
        type=float,
        help="Probability of landing the high-energy charge move during bait scenarios.",
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


_BASE_STATS_REPOSITORY = load_default_base_stats()
_SHADOW_BASELINE_BONUS = 6.0


def _score_from_combat_power(combat_power: int) -> float:
    """Normalise combat power into the 1–100 raid score baseline."""

    scaled = (combat_power - 2000) / 100 + 70
    return max(SCORE_MIN, min(SCORE_MAX, round(scaled, 1)))


def _cp_penalty(combat_power: int | None, *, target_cp: int | None) -> float:
    """Return a penalty for underpowered Pokémon when a target CP is defined."""

    if combat_power is None or target_cp is None:
        return 0.0
    if combat_power >= target_cp:
        return 0.0
    penalty = (target_cp - combat_power) / max(target_cp * 0.1, 1)
    return max(0.0, min(20.0, round(penalty, 1)))


@dataclass(frozen=True)
class TemplateLookup:
    """Describe how a template lookup resolved for a given Pokémon name."""

    entry: PokemonRaidEntry | None
    name_matches: bool
    variant_mismatch: bool


@dataclass(frozen=True)
class _ParsedFastMove:
    """Bundle PvE and PvP fast move definitions derived from CLI input."""

    pve: FastMove
    pvp: PvpFastMove | None


@dataclass(frozen=True)
class _ParsedChargeMove:
    """Bundle PvE and PvP charge move definitions derived from CLI input."""

    pve: ChargeMove
    pvp: PvpChargeMove


def _candidate_base_stat_names(name: str, *, shadow: bool, purified: bool) -> list[str]:
    """Return candidate aliases for resolving base stats."""

    clean = name.strip()
    candidates: list[str] = []
    if clean:
        candidates.append(clean)
        candidates.extend([clean.replace(" ", "-"), clean.replace(" ", "_")])
    if shadow and clean and not clean.lower().startswith("shadow"):
        candidates.insert(0, f"Shadow {clean}")
    if purified and clean and not clean.lower().startswith("purified"):
        candidates.append(f"Purified {clean}")
    return [candidate for candidate in candidates if candidate]


def _resolve_base_stats_entry(
    *,
    species_hint: str | None,
    template: PokemonRaidEntry | None,
    pokemon_name: str | None,
    shadow: bool,
    purified: bool,
) -> BaseStats | None:
    """Return the best matching base stat entry for the provided identifiers."""

    names_to_try: list[str] = []
    for candidate in (species_hint, pokemon_name):
        if candidate:
            names_to_try.extend(
                _candidate_base_stat_names(candidate, shadow=shadow, purified=purified)
            )
    if template:
        for hint in (template.final_form, template.name):
            if hint:
                names_to_try.extend(
                    _candidate_base_stat_names(hint, shadow=shadow, purified=purified)
                )
    seen: set[str] = set()
    for candidate in names_to_try:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            return _BASE_STATS_REPOSITORY.get(candidate)
        except KeyError:
            continue
    return None



def _parse_bool(value: str) -> bool:
    """Return ``True`` or ``False`` for typical CLI boolean tokens."""

    lowered = value.strip().lower()
    if lowered in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"Unrecognised boolean value: {value!r}")


def _parse_extra_tokens(tokens: Sequence[str]) -> dict[str, str]:
    """Return a mapping of extra ``key=value`` tokens."""

    extras: dict[str, str] = {}
    for token in tokens:
        if not token:
            continue
        key, sep, raw_value = token.partition("=")
        key = key.strip().lower()
        if not key:
            raise ValueError("Move descriptor contains an empty extra key.")
        extras[key] = raw_value.strip() if sep else "true"
    return extras


def _parse_fast_move(value: str, *, default_weather: bool) -> _ParsedFastMove:
    """Parse a PvE/PvP fast move descriptor from the CLI."""

    parts = [part.strip() for part in value.split(",")]
    if len(parts) < 4:
        raise ValueError(
            "Fast move descriptor must include name,power,energy_gain,duration."
        )

    name = parts[0]
    try:
        power = float(parts[1])
        energy_gain = float(parts[2])
        duration = float(parts[3])
    except ValueError as exc:  # pragma: no cover - defensive guard.
        raise ValueError("Fast move power, energy gain, and duration must be numeric.") from exc

    extras = _parse_extra_tokens(parts[4:])
    stab = _parse_bool(extras.get("stab", "false"))
    weather = (
        default_weather
        if "weather" not in extras
        else _parse_bool(extras["weather"])
    )
    type_effectiveness = float(extras.get("type", extras.get("effectiveness", "1.0")))

    fast_move = FastMove(
        name=name,
        power=power,
        energy_gain=energy_gain,
        duration=duration,
        stab=stab,
        weather_boosted=weather,
        type_effectiveness=type_effectiveness,
    )

    pvp_fast: PvpFastMove | None = None
    if "turns" in extras:
        try:
            turns_value = float(extras["turns"])
        except ValueError as exc:  # pragma: no cover - defensive guard.
            raise ValueError("Fast move turns must be numeric when provided.") from exc
        if not turns_value.is_integer():
            raise ValueError("Fast move turns must be an integer when provided.")
        turns = int(turns_value)
        if turns <= 0:
            raise ValueError("Fast move turns must be positive when provided.")
        pvp_fast = PvpFastMove(
            name=name,
            damage=power,
            energy_gain=energy_gain,
            turns=turns,
        )

    return _ParsedFastMove(pve=fast_move, pvp=pvp_fast)


def _parse_charge_move(value: str, *, default_weather: bool) -> _ParsedChargeMove:
    """Parse a PvE/PvP charge move descriptor from the CLI."""

    parts = [part.strip() for part in value.split(",")]
    if len(parts) < 4:
        raise ValueError(
            "Charge move descriptor must include name,power,energy_cost,duration."
        )

    name = parts[0]
    try:
        power = float(parts[1])
        energy_cost = float(parts[2])
        duration = float(parts[3])
    except ValueError as exc:  # pragma: no cover - defensive guard.
        raise ValueError(
            "Charge move power, energy cost, and duration must be numeric."
        ) from exc

    extras = _parse_extra_tokens(parts[4:])
    stab = _parse_bool(extras.get("stab", "false"))
    weather = (
        default_weather
        if "weather" not in extras
        else _parse_bool(extras["weather"])
    )
    type_effectiveness = float(extras.get("type", extras.get("effectiveness", "1.0")))

    charge_move = ChargeMove(
        name=name,
        power=power,
        energy_cost=energy_cost,
        duration=duration,
        stab=stab,
        weather_boosted=weather,
        type_effectiveness=type_effectiveness,
    )

    reliability = extras.get("reliability")
    reliability_value = float(reliability) if reliability is not None else None
    has_buff = _parse_bool(extras.get("buff", extras.get("has_buff", "false")))

    pvp_charge = PvpChargeMove(
        name=name,
        damage=power,
        energy_cost=energy_cost,
        reliability=reliability_value,
        has_buff=has_buff,
    )

    return _ParsedChargeMove(pve=charge_move, pvp=pvp_charge)


def _resolve_league_key(league_cap: int | None) -> str:
    """Return the canonical league key for the supplied CP cap."""

    if league_cap is None:
        return "great"
    if league_cap == 1500:
        return "great"
    if league_cap == 2500:
        return "ultra"
    if league_cap <= 0:
        return "master"
    if league_cap not in {cap for cap in (config.cp_cap for config in DEFAULT_LEAGUE_CONFIGS.values()) if cap is not None}:
        raise ValueError(
            "Unsupported league cap; valid values are 1500, 2500, or <=0 for Master League."
        )
    return "master"


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
        return TemplateLookup(entry=None, name_matches=False, variant_mismatch=False)

    variant_mismatch = False
    same_shadow = [entry for entry in matches if entry.shadow == shadow]
    if same_shadow:
        candidates = same_shadow
    elif shadow:
        candidates = matches
        variant_mismatch = True
    else:
        candidates = matches
        variant_mismatch = True

    same_purified = [entry for entry in candidates if entry.purified == purified]
    if same_purified:
        candidates = same_purified
    same_best_buddy = [entry for entry in candidates if entry.best_buddy == best_buddy]
    if same_best_buddy:
        candidates = same_best_buddy

    entry = max(candidates, key=lambda entry: entry.base)
    return TemplateLookup(entry=entry, name_matches=True, variant_mismatch=variant_mismatch)


def _evaluate_single_pokemon(args: argparse.Namespace) -> None:
    """Print a recommendation for a single Pokémon supplied via CLI."""

    if args.combat_power is None or args.pokemon_name is None or args.ivs is None:
        raise SystemExit(
            "--pokemon-name, --combat-power, and --ivs must be provided to evaluate a single Pokémon."
        )

    ivs = tuple(args.ivs)
    wants_pve = bool(
        args.fast_move
        or args.charge_moves
        or args.target_defense is not None
        or args.incoming_dps is not None
        or args.alpha is not None
        or args.weather_boost
    )
    wants_pvp = bool(
        args.league_cap is not None
        or args.beta is not None
        or args.stat_product_reference is not None
        or args.move_pressure_reference is not None
        or args.bait_probability is not None
    )
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

    base_stats_entry: BaseStats | None = None
    if args.base_stats is not None:
        base_stats_tuple = tuple(args.base_stats)
    else:
        base_stats_entry = _resolve_base_stats_entry(
            species_hint=args.species,
            template=template,
            pokemon_name=args.pokemon_name,
            shadow=args.shadow,
            purified=args.purified,
        )
        base_stats_tuple = base_stats_entry.as_tuple() if base_stats_entry else None

    requires_stats = wants_pve or wants_pvp or args.observed_hp is not None
    if requires_stats and base_stats_tuple is None:
        identifier = (
            args.species
            or (template.final_form if template else None)
            or args.pokemon_name
            or "the requested species"
        )
        raise SystemExit(
            f"Unable to locate base stats for {identifier!r}; supply --base-stats or --species with a recognised form identifier."
        )

    shadow_bonus_applied = False
    shadow_baseline_adjusted = False
    if template:
        base_score = template.base
        role = args.role or template.role
        final_form = args.final_form or template.final_form
        if args.shadow and lookup.variant_mismatch and not template.shadow:
            base_score += _SHADOW_BASELINE_BONUS
            shadow_bonus_applied = True
        elif not args.shadow and lookup.variant_mismatch and template.shadow:
            base_score = max(SCORE_MIN, base_score - _SHADOW_BASELINE_BONUS)
            shadow_baseline_adjusted = True
    else:
        base_score = _score_from_combat_power(args.combat_power)
        role = args.role or ""
        final_form = args.final_form or ""
        if args.shadow:
            base_score += _SHADOW_BASELINE_BONUS
            shadow_bonus_applied = True

    base_score = max(SCORE_MIN, min(SCORE_MAX, base_score))
    template_target_cp = template.target_cp if template else None
    if args.target_cp is not None and args.target_cp <= 0:
        raise SystemExit("--target-cp must be a positive integer when provided.")
    target_cp = args.target_cp or template_target_cp
    penalty = _cp_penalty(args.combat_power, target_cp=target_cp)

    template_requires_move = template.requires_special_move if template else False
    template_missing_move = template.needs_tm if template else False
    guidance_requires_move = guidance.needs_tm if guidance else False

    requires_special_move = bool(
        template_requires_move
        or guidance_requires_move
        or template_missing_move
        or args.needs_tm
    )

    if args.has_special_move:
        needs_tm = False
    elif args.needs_tm:
        needs_tm = True
    elif template_missing_move:
        needs_tm = True
    else:
        needs_tm = False

    guidance_note = guidance.note if guidance else None
    template_guidance_note = None
    if template_requires_move and template and template.notes:
        template_guidance_note = f"Guidance: {template.notes}"

    note_parts: list[str] = []
    if args.notes:
        note_parts.append(args.notes)
    if template and template.notes:
        if not (args.has_special_move and template_requires_move):
            note_parts.append(template.notes)
    if guidance_note and not args.has_special_move:
        note_parts.append(guidance_note)
    if shadow_bonus_applied:
        note_parts.append(
            "Applied shadow damage bonus to baseline score due to missing dedicated template."
        )
    if shadow_baseline_adjusted:
        note_parts.append(
            "Adjusted shadow template baseline to approximate non-shadow performance due to missing dedicated template."
        )

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
        target_cp=target_cp,
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
    should_prompt_action = (
        needs_tm or (requires_special_move and not args.has_special_move)
    )
    if should_prompt_action:
        action_note = None
        if guidance_note and not args.has_special_move:
            action_note = guidance_note
        elif template_guidance_note and not args.has_special_move:
            action_note = template_guidance_note
        elif args.notes:
            action_note = args.notes
        elif requires_special_move and not args.has_special_move:
            action_note = "Unlock this Pokémon's exclusive move to reach the listed score."
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

    inferred_stats: dict[str, float | int] | None = None
    inference_error: str | None = None
    species_name = args.species or args.pokemon_name
    if base_stats_entry and base_stats_entry.name:
        species_name = base_stats_entry.name
    if base_stats_tuple is not None:
        base_attack, base_defense, base_stamina = base_stats_tuple
        iv_attack, iv_defense, iv_stamina = ivs
        try:
            level, cpm = infer_level_from_cp(
                base_attack,
                base_defense,
                base_stamina,
                iv_attack,
                iv_defense,
                iv_stamina,
                args.combat_power,
                is_shadow=args.shadow,
                is_best_buddy=args.best_buddy,
                observed_hp=args.observed_hp,
            )
            attack_stat, defense_stat, hp_stat = effective_stats(
                base_attack,
                base_defense,
                base_stamina,
                iv_attack,
                iv_defense,
                iv_stamina,
                level,
                is_shadow=args.shadow,
                is_best_buddy=args.best_buddy,
            )
        except ValueError as exc:
            inference_error = str(exc)
        else:
            inferred_stats = {
                "level": level,
                "cpm": cpm,
                "attack": attack_stat,
                "defense": defense_stat,
                "hp": hp_stat,
            }

    parsed_fast: _ParsedFastMove | None = None
    parsed_charges: list[_ParsedChargeMove] = []
    if args.fast_move:
        try:
            parsed_fast = _parse_fast_move(args.fast_move, default_weather=args.weather_boost)
        except ValueError as exc:
            raise SystemExit(f"Failed to parse --fast: {exc}") from exc
    if args.charge_moves:
        try:
            parsed_charges = [
                _parse_charge_move(move, default_weather=args.weather_boost)
                for move in args.charge_moves
            ]
        except ValueError as exc:
            raise SystemExit(f"Failed to parse --charge: {exc}") from exc

    if wants_pve and inferred_stats is None:
        raise SystemExit(
            "PvE scoring requires base stats and CP/IVs to infer effective stats."
        )
    if wants_pvp and inferred_stats is None:
        raise SystemExit(
            "PvP scoring requires base stats and CP/IVs to infer effective stats."
        )

    if inferred_stats:
        print()
        print("Inferred build stats")
        print("--------------------")
        print(f"Species: {species_name}")
        print(f"Level: {inferred_stats['level']:.1f}")
        print(f"CPM: {inferred_stats['cpm']:.6f}")
        print(f"Effective Attack: {inferred_stats['attack']:.2f}")
        print(f"Effective Defense: {inferred_stats['defense']:.2f}")
        print(f"Effective HP: {int(inferred_stats['hp'])}")
    elif inference_error:
        print()
        print(f"Level inference failed: {inference_error}")

    pve_output: dict[str, float | Counter[str]] | None = None
    if wants_pve:
        if parsed_fast is None:
            raise SystemExit("PvE scoring requires a fast move descriptor via --fast.")
        if not parsed_charges:
            raise SystemExit("PvE scoring requires at least one --charge descriptor.")
        if args.target_defense is None:
            raise SystemExit("PvE scoring requires --target-defense.")
        if args.incoming_dps is None:
            raise SystemExit("PvE scoring requires --incoming-dps.")
        alpha_value = args.alpha if args.alpha is not None else 0.6
        pve_output = compute_pve_score(
            inferred_stats["attack"],
            inferred_stats["defense"],
            int(inferred_stats["hp"]),
            parsed_fast.pve,
            [move.pve for move in parsed_charges],
            target_defense=args.target_defense,
            incoming_dps=args.incoming_dps,
            alpha=alpha_value,
        )

    pvp_output: dict[str, float] | None = None
    pvp_league = "great"
    if wants_pvp:
        if parsed_fast is None:
            raise SystemExit("PvP scoring requires a fast move descriptor via --fast.")
        if parsed_fast.pvp is None:
            raise SystemExit("PvP scoring requires --fast to include turns=... for PvP timing.")
        if not parsed_charges:
            raise SystemExit("PvP scoring requires at least one --charge descriptor.")
        try:
            pvp_league = _resolve_league_key(args.league_cap)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        pvp_output = compute_pvp_score(
            inferred_stats["attack"],
            inferred_stats["defense"],
            int(inferred_stats["hp"]),
            parsed_fast.pvp,
            [move.pvp for move in parsed_charges],
            league=pvp_league,
            beta=args.beta,
            stat_product_reference=args.stat_product_reference,
            move_pressure_reference=args.move_pressure_reference,
            bait_probability=args.bait_probability,
            league_configs=DEFAULT_LEAGUE_CONFIGS,
        )

    if pve_output:
        alpha_value = pve_output.get("alpha", args.alpha if args.alpha is not None else 0.6)
        charge_usage = pve_output["charge_usage_per_cycle"]
        charge_summary = ", ".join(
            f"{name}: {count:.2f}" for name, count in sorted(charge_usage.items())
        )
        if not charge_summary:
            charge_summary = "None"
        print()
        print("PvE value")
        print("---------")
        print(f"Rotation DPS: {pve_output['dps']:.2f}")
        print(f"Cycle Damage: {pve_output['cycle_damage']:.2f}")
        print(f"Cycle Time: {pve_output['cycle_time']:.2f}s")
        print(f"Fast Moves / Cycle: {pve_output['fast_moves_per_cycle']:.2f}")
        print(f"Charge Use / Cycle: {charge_summary}")
        print(f"EHP: {pve_output['ehp']:.2f}")
        print(f"TDO: {pve_output['tdo']:.2f}")
        print(f"PvE Value (alpha={alpha_value:.2f}): {pve_output['value']:.2f}")

    if pvp_output:
        league_label = pvp_league.capitalize()
        beta_value = args.beta if args.beta is not None else 0.52
        print()
        print(f"PvP value ({league_label} League)")
        print("---------------------------")
        print(f"Stat Product: {pvp_output['stat_product']:.2f}")
        print(
            f"Normalised Stat Product: {pvp_output['stat_product_normalised']:.4f}"
        )
        print(f"Move Pressure: {pvp_output['move_pressure']:.2f}")
        print(
            f"Normalised Move Pressure: {pvp_output['move_pressure_normalised']:.4f}"
        )
        print(f"PvP Score (beta={beta_value:.2f}): {pvp_output['score']:.4f}")


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




