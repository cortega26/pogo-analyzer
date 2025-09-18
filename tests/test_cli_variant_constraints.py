"""CLI constraints for Shadow/Purified/Lucky combinations."""

from __future__ import annotations

import pytest

import raid_scoreboard_generator as rsg


def _run(argv: list[str]) -> None:
    rsg.main(argv)


def test_reject_shadow_and_purified_together(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _run([
            "--pokemon-name", "Testmon",
            "--combat-power", "1000",
            "--ivs", "10", "10", "10",
            "--shadow",
            "--purified",
        ])


def test_reject_shadow_and_lucky_together(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        _run([
            "--pokemon-name", "Testmon",
            "--combat-power", "1000",
            "--ivs", "10", "10", "10",
            "--shadow",
            "--lucky",
        ])

