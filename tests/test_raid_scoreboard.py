"""Regression tests for the raid scoreboard generator."""

from __future__ import annotations

import copy
import json
import re
import math
from pathlib import Path

import pytest

import pogo_analyzer as pa
import raid_scoreboard_generator as rsg
from pogo_analyzer.cpm_table import get_cpm
from pogo_analyzer.formulas import effective_stats, infer_level_from_cp
from pogo_analyzer.pve import ChargeMove, FastMove, compute_pve_score
from pogo_analyzer.pvp import (
    DEFAULT_LEAGUE_CONFIGS,
    PvpChargeMove,
    PvpFastMove,
    compute_pvp_score,
)


def _compute_cp(
    base_attack: int,
    base_defense: int,
    base_stamina: int,
    iv_attack: int,
    iv_defense: int,
    iv_stamina: int,
    level: float,
    *,
    is_shadow: bool = False,
    is_best_buddy: bool = False,
) -> int:
    """Compute CP using the specification from :mod:`pogo_analyzer.formulas`."""

    attack = (base_attack + iv_attack) * (1.2 if is_shadow else 1.0)
    defense = (base_defense + iv_defense) * (0.83 if is_shadow else 1.0)
    stamina = base_stamina + iv_stamina
    cpm = get_cpm(level + (1.0 if is_best_buddy else 0.0))
    return math.floor(attack * math.sqrt(defense) * math.sqrt(stamina) * cpm**2 / 10)


@pytest.fixture(autouse=True)
def clear_scoreboard_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure configuration environment variables do not leak between tests."""

    for name in {
        "RAID_SCOREBOARD_OUTPUT_DIR",
        "RAID_SCOREBOARD_CSV",
        "RAID_SCOREBOARD_EXCEL",
        "RAID_SCOREBOARD_DISABLE_EXCEL",
        "RAID_SCOREBOARD_PREVIEW_LIMIT",
    }:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def tmp_workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Execute the scoreboard generator from an isolated working directory."""

    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_missing_pandas_skips_excel_export(
    tmp_workdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ensure the user guidance is correct when pandas isn't available."""

    monkeypatch.setattr(rsg, "pd", None)
    result = rsg.main(argv=[])
    assert result is not None
    out = capsys.readouterr().out

    assert "install pandas" in out
    assert result.csv_path.exists()
    assert result.excel_path is not None
    assert not result.excel_written
    assert not result.excel_path.exists()


def test_simple_table_column_management() -> None:
    """SimpleTable should preserve column order and guard against missing columns."""

    rows = [{"a": 1, "b": 2}, {"b": 3, "c": 4}]
    table = rsg.SimpleTable(rows)

    assert table._columns == ["a", "b", "c"]  # type: ignore[attr-defined]
    assert table._rows[0]["c"] == ""  # type: ignore[attr-defined]

    table["d"] = [5, 6]
    assert table._columns == ["a", "b", "c", "d"]  # type: ignore[attr-defined]
    assert [row["d"] for row in table._rows] == [5, 6]  # type: ignore[attr-defined]

    with pytest.raises(KeyError):
        _ = table["missing"]
    with pytest.raises(KeyError):
        table.sort_values("missing")


def test_simple_table_reset_index_adds_position_column() -> None:
    """reset_index should prepend an index column without mutating existing data."""

    rows = [{"value": 10}, {"value": 20}]
    table = rsg.SimpleTable(rows)

    reset = table.reset_index()

    assert reset._columns[0] == "index"  # type: ignore[attr-defined]
    assert [row["index"] for row in reset._rows] == [0, 1]  # type: ignore[attr-defined]
    assert [row["value"] for row in reset._rows] == [10, 20]  # type: ignore[attr-defined]


def test_simple_table_reset_index_preserves_existing_index_column() -> None:
    """Existing "index" columns should be kept when adding the positional index."""

    rows = [{"index": "Alpha", "value": 1}, {"index": "Beta", "value": 2}]
    table = rsg.SimpleTable(rows)

    reset = table.reset_index()

    assert reset._columns[:3] == ["level_0", "index", "value"]  # type: ignore[attr-defined]
    assert [row["level_0"] for row in reset._rows] == [0, 1]  # type: ignore[attr-defined]
    assert [row["index"] for row in reset._rows] == ["Alpha", "Beta"]  # type: ignore[attr-defined]


def test_pokemon_entry_row_generation() -> None:
    """PokemonRaidEntry should format names, IVs, and scores consistently."""

    entry = rsg.PokemonRaidEntry(
        "Tester",
        (15, 14, 13),
        final_form="Mega Tester",
        role="Support",
        base=81,
        lucky=True,
        shadow=True,
        requires_special_move=True,
        needs_tm=True,
        mega_soon=True,
        notes="Example entry for unit tests.",
    )
    row = entry.as_row()
    expected_score = rsg.raid_score(
        81,
        rsg.iv_bonus(15, 14, 13),
        lucky=True,
        needs_tm=True,
        mega_bonus_soon=True,
        mega_bonus_now=False,
    )
    assert row["Your Pokémon"] == "Tester (lucky) (shadow)"
    assert row["IV (Atk/Def/Sta)"] == "15/14/13"
    assert row["Move Needs (CD/ETM?)"] == "Yes"
    assert row["Mega Available"] == "Soon"
    assert row["Raid Score (1-100)"] == expected_score


def test_build_dataframe_allows_custom_entries() -> None:
    """Custom entry sequences should build into data frames or tables."""

    entry = rsg.PokemonRaidEntry(
        "Solo",
        (10, 11, 12),
        final_form="Final",
        role="Utility",
        base=70,
        notes="Single test entry.",
    )
    df = rsg.build_dataframe([entry])
    if isinstance(df, rsg.SimpleTable):
        data_row = df._rows[0]  # type: ignore[attr-defined]
    else:
        data_row = df.iloc[0].to_dict()
    assert data_row["Your Pokémon"] == "Solo"
    assert data_row["Final Raid Form"] == "Final"
    assert data_row["Primary Role"] == "Utility"


def test_add_priority_tier_assigns_expected_labels() -> None:
    """Threshold boundaries should map onto documented priority tiers."""

    table = rsg.SimpleTable(
        [
            {"Raid Score (1-100)": 90.0},
            {"Raid Score (1-100)": 86.0},
            {"Raid Score (1-100)": 78.0},
            {"Raid Score (1-100)": 70.0},
            {"Raid Score (1-100)": 65.0},
        ]
    )
    tiered = rsg.add_priority_tier(table)
    tiers = [row["Priority Tier"] for row in tiered._rows]  # type: ignore[attr-defined]
    assert tiers == [
        "S (Build ASAP)",
        "A (High)",
        "B (Good)",
        "C (Situational)",
        "D (Doesn't belong on a Raids list)",
    ]


def test_parse_fast_move_rejects_fractional_turns() -> None:
    """Fractional turn values should fail fast to guard against malformed inputs."""

    with pytest.raises(ValueError, match="Fast move turns must be an integer"):
        rsg._parse_fast_move(
            "Example Fast,10,5,0.5,turns=1.5",
            default_weather=False,
        )


def test_canonical_api_aliases() -> None:
    """New naming exports should remain in sync with legacy helpers."""

    entry = pa.DEFAULT_RAID_ENTRIES[0]
    canonical_rows = pa.build_entry_rows([entry])
    legacy_rows = rsg.build_rows([entry])
    assert canonical_rows == legacy_rows

    attack, defence, stamina = entry.ivs
    canonical_score = pa.calculate_raid_score(
        entry.base,
        pa.calculate_iv_bonus(attack, defence, stamina),
        lucky=entry.lucky,
        needs_tm=entry.needs_tm,
        mega_bonus_now=entry.mega_now,
        mega_bonus_soon=entry.mega_soon,
    )
    legacy_score = rsg.raid_score(
        entry.base,
        rsg.iv_bonus(attack, defence, stamina),
        lucky=entry.lucky,
        needs_tm=entry.needs_tm,
        mega_bonus_now=entry.mega_now,
        mega_bonus_soon=entry.mega_soon,
    )
    assert canonical_score == legacy_score


def test_cli_regular_magnezone_uses_shadow_template_metadata(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Non-shadow evaluations should reuse shadow templates with adjusted baselines."""

    created_entries: list[rsg.PokemonRaidEntry] = []
    real_entry_cls = rsg.PokemonRaidEntry

    def capture_entry(*args: object, **kwargs: object) -> rsg.PokemonRaidEntry:
        entry = real_entry_cls(*args, **kwargs)
        created_entries.append(entry)
        return entry

    monkeypatch.setattr(rsg, "PokemonRaidEntry", capture_entry)

    args = rsg.parse_args(
        [
            "--pokemon-name",
            "Magnemite",
            "--combat-power",
            "3200",
            "--ivs",
            "15",
            "15",
            "15",
        ]
    )

    rsg._evaluate_single_pokemon(args)
    out = capsys.readouterr().out

    assert created_entries, "expected evaluation to instantiate a raid entry"
    entry = created_entries[-1]

    lookup = rsg._template_entry(
        "Magnemite", shadow=False, purified=False, best_buddy=False
    )
    template = lookup.entry
    assert template is not None
    assert lookup.variant_mismatch and template.shadow

    expected_base = max(rsg.SCORE_MIN, template.base - rsg._SHADOW_BASELINE_BONUS)
    assert entry.base == expected_base
    assert entry.final_form == template.final_form
    assert entry.role == template.role
    assert template.notes in entry.notes
    assert "Adjusted shadow template baseline" in entry.notes

    row = entry.to_row()
    expected_score = rsg.raid_score(expected_base, rsg.iv_bonus(*entry.ivs))
    assert row["Raid Score (1-100)"] == expected_score
    assert f"Raid Score: {expected_score}/100" in out


def _single_eval(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[float, str]:
    """Invoke the CLI for a single Pokémon and return the score with raw output."""

    capsys.readouterr()
    rsg.main(argv)
    captured = capsys.readouterr().out
    match = re.search(r"Raid Score: ([0-9]+\.[0-9])", captured)
    assert match, f"Raid score not found in output:\n{captured}"
    return float(match.group(1)), captured


def test_shadow_bonus_applied_for_template_fallback(capsys: pytest.CaptureFixture[str]) -> None:
    """Shadow evaluations without templates should receive the baseline bonus."""

    base_args = [
        "--pokemon-name",
        "Charmander",
        "--combat-power",
        "203",
        "--ivs",
        "12",
        "7",
        "9",
    ]
    regular_score, regular_output = _single_eval(base_args, capsys)
    shadow_score, shadow_output = _single_eval(base_args + ["--shadow"], capsys)

    assert pytest.approx(regular_score, rel=0, abs=0.01) == 54.1
    assert pytest.approx(shadow_score, rel=0, abs=0.01) == 60.1
    assert shadow_score - regular_score == pytest.approx(6.0, rel=0, abs=0.01)
    assert "Applied shadow damage bonus" in shadow_output
    assert "Applied shadow damage bonus" not in regular_output


def test_shadow_bonus_applied_when_template_variant_missing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When only the regular template exists, add the same baseline shadow bonus."""

    base_args = [
        "--pokemon-name",
        "Snover",
        "--combat-power",
        "1234",
        "--ivs",
        "15",
        "13",
        "12",
    ]
    regular_score, _ = _single_eval(base_args, capsys)
    shadow_score, shadow_output = _single_eval(base_args + ["--shadow"], capsys)

    assert shadow_score - regular_score == pytest.approx(6.0, rel=0, abs=0.01)
    assert "Applied shadow damage bonus" in shadow_output



def test_single_pokemon_inference_and_scoring_outputs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Single Pokémon evaluation should emit inferred stats and PvE/PvP scores."""

    base_stats = (256, 188, 216)
    ivs = (15, 15, 15)
    level = 35.0
    cp = _compute_cp(*base_stats, *ivs, level)

    argv = [
        "--pokemon-name",
        "Hydreigon",
        "--species",
        "Hydreigon",
        "--base-stats",
        *map(str, base_stats),
        "--cp",
        str(cp),
        "--ivs",
        *map(str, ivs),
        "--fast",
        "Snarl,12,13,1.0,turns=4,stab=true",
        "--charge",
        "Brutal Swing,65,40,1.9,stab=true",
        "--target-defense",
        "180",
        "--incoming-dps",
        "35",
        "--alpha",
        "0.6",
        "--league-cap",
        "1500",
        "--beta",
        "0.52",
    ]

    capsys.readouterr()
    rsg.main(argv)
    out = capsys.readouterr().out

    level_estimate, cpm_estimate = infer_level_from_cp(*base_stats, *ivs, cp)
    attack, defense, hp = effective_stats(*base_stats, *ivs, level_estimate)
    pve_expected = compute_pve_score(
        attack,
        defense,
        hp,
        FastMove("Snarl", 12.0, 13.0, 1.0, stab=True),
        [ChargeMove("Brutal Swing", 65.0, 40.0, 1.9, stab=True)],
        target_defense=180.0,
        incoming_dps=35.0,
        alpha=0.6,
    )
    pvp_expected = compute_pvp_score(
        attack,
        defense,
        hp,
        PvpFastMove("Snarl", damage=12.0, energy_gain=13.0, turns=4),
        [PvpChargeMove("Brutal Swing", damage=65.0, energy_cost=40.0)],
        league="great",
        beta=0.52,
        league_configs=DEFAULT_LEAGUE_CONFIGS,
    )

    assert f"Level: {level_estimate:.1f}" in out
    assert f"CPM: {cpm_estimate:.6f}" in out
    assert f"Effective Attack: {attack:.2f}" in out
    assert f"Rotation DPS: {pve_expected['dps']:.2f}" in out
    assert f"PvE Value (alpha=0.60): {pve_expected['value']:.2f}" in out
    assert f"PvP Score (beta=0.52): {pvp_expected['score']:.4f}" in out


def test_name_normalisation_handles_forms() -> None:
    """normalise_name should retain meaningful form descriptors."""

    assert rsg.normalise_name('Giratina (Origin Forme)') == 'giratina-origin'
    assert rsg.normalise_name('Giratina (Altered)') == 'giratina-altered'
    assert rsg.normalise_name('Flabebe (lucky)') == 'flabebe'
    assert rsg.normalise_name('Gengar (hundo)') == 'gengar'


def test_dataset_requires_special_move_not_penalized() -> None:
    """Entries that need special moves should retain full scores by default."""

    entry = next(e for e in pa.DEFAULT_RAID_ENTRIES if e.requires_special_move)
    row = entry.to_row()

    assert entry.requires_special_move
    assert entry.needs_tm is False
    assert row["Move Needs (CD/ETM?)"] == "Yes"


def test_special_move_entries_have_guidance_or_notes() -> None:
    """Every special-move template should provide actionable guidance."""

    for entry in pa.DEFAULT_RAID_ENTRIES:
        if not entry.requires_special_move:
            continue
        has_guidance = rsg.get_move_guidance(entry.name) is not None
        assert has_guidance or entry.notes, f"Missing guidance for {entry.name}"


def test_load_raid_entries_matches_default_dataset() -> None:
    """The JSON-backed loader should reproduce the packaged dataset."""

    loaded = pa.load_raid_entries()
    assert loaded == pa.DEFAULT_RAID_ENTRIES


def test_load_raid_entries_missing_required_field(tmp_path: Path) -> None:
    """Entries lacking required columns should raise a validation error."""

    payload = {
        "metadata": copy.deepcopy(pa.DEFAULT_RAID_ENTRY_METADATA),
        "entries": [
            {
                "ivs": [15, 15, 15],
                "base": 80,
            }
        ],
    }
    target = tmp_path / "invalid_missing_field.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=r"missing required field\(s\): name"):
        pa.load_raid_entries(target)


def test_load_raid_entries_rejects_out_of_range_score(tmp_path: Path) -> None:
    """Base scores outside the allowed range should be rejected."""

    payload = {
        "metadata": copy.deepcopy(pa.DEFAULT_RAID_ENTRY_METADATA),
        "entries": [
            {
                "name": "Broken",
                "ivs": [15, 15, 15],
                "base": 150,
            }
        ],
    }
    target = tmp_path / "invalid_score.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError, match=r"Raid entry 'Broken' is invalid: .*base must fall within"
    ):
        pa.load_raid_entries(target)


def test_pokemon_entry_validation_rejects_bad_inputs() -> None:
    """Dataclass construction enforces score and IV constraints."""

    with pytest.raises(ValueError):
        rsg.PokemonRaidEntry("", (15, 15, 15))
    with pytest.raises(ValueError):
        rsg.PokemonRaidEntry("Bad IVs", (16, 0, 0))
    with pytest.raises(ValueError):
        rsg.PokemonRaidEntry("Low base", (15, 15, 15), base=0)
    with pytest.raises(TypeError):
        rsg.PokemonRaidEntry("Float IV", (15, 15, 15.0))  # type: ignore[arg-type]


def test_single_pokemon_shadow_template_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When only a shadow template exists, normal forms should reuse it with an adjusted baseline."""

    rsg.main(
        argv=[
            "--pokemon-name",
            "Giratina",
            "--combat-power",
            "3000",
            "--ivs",
            "15",
            "15",
            "15",
        ]
    )
    normal_out = capsys.readouterr().out

    rsg.main(
        argv=[
            "--pokemon-name",
            "Giratina",
            "--combat-power",
            "3000",
            "--ivs",
            "15",
            "15",
            "15",
            "--shadow",
        ]
    )
    shadow_out = capsys.readouterr().out

    score_pattern = re.compile(r"Raid Score: ([0-9]+\.?[0-9]*)/100")
    normal_match = score_pattern.search(normal_out)
    shadow_match = score_pattern.search(shadow_out)
    assert normal_match and shadow_match
    normal_score = float(normal_match.group(1))
    shadow_score = float(shadow_match.group(1))

    assert shadow_score > normal_score
    assert shadow_score - normal_score == pytest.approx(rsg._SHADOW_BASELINE_BONUS)
    assert "Adjusted shadow template baseline" in normal_out


def test_single_pokemon_shadow_vs_normal_diff(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Shadow variants should receive a higher baseline than regular forms."""

    rsg.main(
        argv=[
            "--pokemon-name",
            "Larvitar",
            "--combat-power",
            "371",
            "--ivs",
            "11",
            "14",
            "14",
        ]
    )
    normal_out = capsys.readouterr().out

    rsg.main(
        argv=[
            "--pokemon-name",
            "Larvitar",
            "--combat-power",
            "371",
            "--ivs",
            "11",
            "14",
            "14",
            "--shadow",
        ]
    )
    shadow_out = capsys.readouterr().out

    score_pattern = re.compile(r"Raid Score: ([0-9]+\.?[0-9]*)/100")
    normal_match = score_pattern.search(normal_out)
    shadow_match = score_pattern.search(shadow_out)
    assert normal_match and shadow_match
    normal_score = float(normal_match.group(1))
    shadow_score = float(shadow_match.group(1))

    assert shadow_score > normal_score
    assert "Shadow" in shadow_out
    assert "Shadow" not in normal_out


def test_single_pokemon_cli_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:


    """The CLI should print a recommendation when a single Pokémon is supplied."""

    result = rsg.main(
        argv=[
            "--pokemon-name",
            "Hydreigon",
            "--combat-power",
            "3200",
            "--ivs",
            "15",
            "14",
            "15",
            "--shadow",
            "--needs-tm",
            "--notes",
            "Community Day move required.",
        ]
    )
    out = capsys.readouterr().out

    assert result is None
    assert "Hydreigon" in out
    assert "Raid Score" in out
    assert "Priority Tier" in out
    assert "Recommended Charged Move" in out
    assert "Exclusive move missing" in out


def test_single_pokemon_cli_has_special_move_avoids_penalty(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Users confirming the special move should avoid the default penalty."""

    args = [
        "--pokemon-name",
        "Hydreigon",
        "--combat-power",
        "3200",
        "--ivs",
        "15",
        "14",
        "15",
    ]
    rsg.main(argv=args)
    missing_out = capsys.readouterr().out

    rsg.main(argv=args + ["--has-special-move"])
    has_out = capsys.readouterr().out

    score_pattern = re.compile(r"Raid Score: ([0-9]+\.?[0-9]*)/100")
    missing_match = score_pattern.search(missing_out)
    has_match = score_pattern.search(has_out)
    assert missing_match and has_match
    assert float(has_match.group(1)) == float(missing_match.group(1))

    assert "Action:" in missing_out
    assert "Underpowered" not in missing_out
    assert "Exclusive move missing" not in missing_out
    assert "Exclusive move missing" not in has_out
    assert "Exclusive move already unlocked." in has_out



def test_single_pokemon_cli_target_cp_penalty(capsys: pytest.CaptureFixture[str]) -> None:
    """Target CP should drive underpowered messaging when supplied."""

    rsg.main(
        argv=[
            "--pokemon-name",
            "Crawdaunt",
            "--combat-power",
            "1200",
            "--ivs",
            "10",
            "10",
            "10",
        ]
    )
    out_without_target = capsys.readouterr().out

    rsg.main(
        argv=[
            "--pokemon-name",
            "Crawdaunt",
            "--combat-power",
            "1200",
            "--ivs",
            "10",
            "10",
            "10",
            "--target-cp",
            "3000",
        ]
    )
    out_with_target = capsys.readouterr().out

    assert "Underpowered" not in out_without_target
    assert "Underpowered" in out_with_target


def test_single_pokemon_cli_dataset_target_cp(capsys: pytest.CaptureFixture[str]) -> None:
    """Templates can define target CP values for automatic underpowered checks."""

    rsg.main(
        argv=[
            "--pokemon-name",
            "Beldum",
            "--combat-power",
            "1500",
            "--ivs",
            "10",
            "10",
            "10",
        ]
    )
    out = capsys.readouterr().out

    assert "Underpowered" in out


def test_single_pokemon_cli_guidance_fallback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """CLI should fall back to template notes when move guidance is missing."""

    monkeypatch.setattr(rsg, "get_move_guidance", lambda *_: None)
    rsg.main(
        argv=[
            "--pokemon-name",
            "Beldum",
            "--combat-power",
            "600",
            "--ivs",
            "13",
            "13",
            "13",
        ]
    )
    out = capsys.readouterr().out

    assert "Action: Guidance: Meteor Mash is mandatory; top Steel attacker when built." in out


def test_main_respects_env_configuration(
    tmp_workdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Environment variables should override defaults and allow disabling Excel."""

    output_dir = tmp_workdir / "exports"
    monkeypatch.setenv("RAID_SCOREBOARD_OUTPUT_DIR", str(output_dir))
    monkeypatch.setenv("RAID_SCOREBOARD_CSV", "custom.csv")
    monkeypatch.setenv("RAID_SCOREBOARD_DISABLE_EXCEL", "true")
    monkeypatch.setenv("RAID_SCOREBOARD_PREVIEW_LIMIT", "2")

    result = rsg.main(argv=[])
    assert result is not None
    out = capsys.readouterr().out

    expected_csv = (output_dir / "custom.csv").resolve()
    assert result.csv_path == expected_csv
    assert result.csv_path.exists()
    assert "Top 2 preview" in out
    assert "disabled via configuration" in out
    assert result.excel_path is None
