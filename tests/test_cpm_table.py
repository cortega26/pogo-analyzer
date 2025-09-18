"""Tests for CPM table boundaries and increments."""

from __future__ import annotations

import pytest

from pogo_analyzer.cpm_table import CPM, get_cpm


def test_get_cpm_valid_boundaries() -> None:
    assert get_cpm(1.0) == pytest.approx(CPM[1.0])
    assert get_cpm(51.0) == pytest.approx(CPM[51.0])


@pytest.mark.parametrize("level", [0.5, 52.0, -1.0])
def test_get_cpm_out_of_range(level: float) -> None:
    with pytest.raises(ValueError):
        get_cpm(level)


def test_get_cpm_requires_half_level_steps() -> None:
    with pytest.raises(ValueError):
        get_cpm(10.25)

