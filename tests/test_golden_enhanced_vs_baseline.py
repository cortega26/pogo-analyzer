"""Golden-drift tests: baseline vs --enhanced-defaults outputs.

These tests intentionally parse a small, stable subset of the CLI output to
detect changes when opting into the enhanced-defaults bundle. They avoid
fragile full-text comparisons.
"""

from __future__ import annotations

import re

import pytest

import raid_scoreboard_generator as rsg


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    capsys.readouterr()
    rsg.main(argv)
    return capsys.readouterr().out


def _extract_float(pattern: str, text: str) -> float:
    match = re.search(pattern, text)
    assert match, f"pattern not found: {pattern}\n{text}"
    return float(match.group(1))


def _common_args() -> list[str]:
    return [
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
    ]


def test_pve_pvp_scores_change_with_enhanced_defaults(capsys: pytest.CaptureFixture[str]) -> None:
    base_out = _run(_common_args(), capsys)
    enh_out = _run(_common_args() + ["--enhanced-defaults"], capsys)

    # Extract PvE value and PvP score lines
    base_pve = _extract_float(r"PvE Value \(alpha=[0-9.]+\): ([0-9.]+)", base_out)
    base_pvp = _extract_float(r"PvP Score \(beta=[0-9.]+\): ([0-9.]+)", base_out)
    enh_pve = _extract_float(r"PvE Value \(alpha=[0-9.]+\): ([0-9.]+)", enh_out)
    enh_pvp = _extract_float(r"PvP Score \(beta=[0-9.]+\): ([0-9.]+)", enh_out)

    # Scores should differ when enhanced defaults are enabled
    assert abs(base_pve - enh_pve) > 1e-9
    assert abs(base_pvp - enh_pvp) > 1e-12

