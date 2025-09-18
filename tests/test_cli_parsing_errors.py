"""CLI parsing errors and override precedence tests."""

from __future__ import annotations

import re

import pytest

import raid_scoreboard_generator as rsg


def _run_cli(argv: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    capsys.readouterr()
    rsg.main(argv)
    return capsys.readouterr().out


def test_cli_invalid_fast_move_numbers_surface_clean_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _run_cli(
            [
                "--pokemon-name",
                "Testmon",
                "--combat-power",
                "1000",
                "--ivs",
                "10",
                "10",
                "10",
                "--fast",
                "Quick,notnum,13,1.0",
            ],
            capsys,
        )


def test_cli_invalid_boolean_token_in_move_descriptor(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _run_cli(
            [
                "--pokemon-name",
                "Testmon",
                "--combat-power",
                "1000",
                "--ivs",
                "10",
                "10",
                "10",
                "--fast",
                "Quick,10,10,1.0,weather=maybe",
            ],
            capsys,
        )


def test_cli_unsupported_league_cap_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _run_cli(
            [
                "--pokemon-name",
                "Hydreigon",
                "--species",
                "Hydreigon",
                "--base-stats",
                "256",
                "188",
                "211",
                "--combat-power",
                "3325",
                "--ivs",
                "15",
                "15",
                "15",
                "--fast",
                "Snarl,12,13,1.0,turns=4,stab=true",
                "--charge",
                "Brutal Swing,65,40,1.9,stab=true",
                "--target-defense",
                "180",
                "--incoming-dps",
                "35",
                "--league-cap",
                "1234",
            ],
            capsys,
        )


def test_cli_enhanced_defaults_yield_to_explicit_overrides(capsys: pytest.CaptureFixture[str]) -> None:
    out = _run_cli(
        [
            "--pokemon-name",
            "Hydreigon",
            "--species",
            "Hydreigon",
            "--base-stats",
            "256",
            "188",
            "211",
            "--combat-power",
            "3325",
            "--ivs",
            "15",
            "15",
            "15",
            "--fast",
            "Snarl,12,13,1.0,turns=4,stab=true",
            "--charge",
            "Brutal Swing,65,40,1.9,stab=true",
            "--target-defense",
            "180",
            "--incoming-dps",
            "35",
            "--league-cap",
            "1500",
            "--enhanced-defaults",
            "--shield-weights",
            "1.0",
            "0.0",
            "0.0",
        ],
        capsys,
    )
    # Ensure the override wins: look for weight=1.00 on shields=0 scenario line
    match = re.search(r"shields=0, weight=1\.00", out)
    assert match, f"shield weight override not reflected in output:\n{out}"

