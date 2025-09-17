from __future__ import annotations

import pytest

from pogo_analyzer.cpm_table import CPM, get_cpm


@pytest.mark.parametrize(
    ("level", "expected"),
    [
        (1.0, CPM[1.0]),
        (25.5, CPM[25.5]),
        (40.5, CPM[40.5]),
        (51.0, CPM[51.0]),
    ],
)
def test_get_cpm_returns_expected_multiplier(level: float, expected: float) -> None:
    assert get_cpm(level) == expected


@pytest.mark.parametrize("level", [0.5, 52.0])
def test_get_cpm_rejects_out_of_range_levels(level: float) -> None:
    with pytest.raises(ValueError, match="outside the supported range"):
        get_cpm(level)


@pytest.mark.parametrize("level", [10.25, 40.333333])
def test_get_cpm_rejects_non_half_step(level: float) -> None:
    with pytest.raises(ValueError, match="0.5 increments"):
        get_cpm(level)


def test_get_cpm_requires_numeric_input() -> None:
    with pytest.raises(TypeError):
        get_cpm("20")  # type: ignore[arg-type]
