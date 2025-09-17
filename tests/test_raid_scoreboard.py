"""Regression tests for the raid scoreboard generator."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

import pogo_analyzer as pa
import raid_scoreboard_generator as rsg


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
    """When only a shadow template exists, normal forms should fall back to CP heuristics."""

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
    assert normal_score < 90


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
