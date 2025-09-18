"""CLI tests for enhanced defaults and new toggles.

These tests exercise the opt-in enhanced defaults bundle and a couple of
parsing/printing paths to ensure the CLI remains stable and secure.
"""

from __future__ import annotations

import re

import pytest

import raid_scoreboard_generator as rsg


def _run_cli(argv: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    capsys.readouterr()  # clear buffer
    rsg.main(argv)
    return capsys.readouterr().out


def test_enhanced_defaults_enable_pve_energy_and_relobby(capsys: pytest.CaptureFixture[str]) -> None:
    """--enhanced-defaults should turn on PvE energy-from-damage and relobby penalty."""

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
            "--alpha",
            "0.6",
            "--enhanced-defaults",
        ],
        capsys,
    )

    # PvE section should include energy ratio and relobby note when enabled.
    assert "PvE value" in out
    assert "Energy from damage ratio: 0.50" in out
    assert "Relobby penalty applied" in out


def test_enhanced_defaults_enable_pvp_shield_blend_and_bait_model(capsys: pytest.CaptureFixture[str]) -> None:
    """--enhanced-defaults should enable shield blending and a bait model by default."""

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
            "--beta",
            "0.52",
            "--enhanced-defaults",
        ],
        capsys,
    )

    # PvP section should include shield breakdown with implied weights and bait probabilities.
    assert "PvP value (Great League)" in out
    assert "Shield scenarios:" in out
    # Ensure bait probability printout is present in at least one line
    assert re.search(r"bait=\d+\.\d+", out)


def test_cli_rejects_invalid_bait_model(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Invalid --bait-model strings should raise a parse error with a clear message."""

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
                "1500",
                "--beta",
                "0.52",
                "--bait-model",
                "a=oops",  # non-numeric
            ],
            capsys,
        )

