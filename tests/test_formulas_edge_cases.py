"""Edge case tests for infer_level_from_cp and damage helpers."""

from __future__ import annotations

import pytest

from pogo_analyzer.formulas import infer_level_from_cp


def test_infer_level_negative_cp_raises() -> None:
    with pytest.raises(ValueError):
        infer_level_from_cp(100, 100, 100, 10, 10, 10, -1)


def test_infer_level_negative_observed_hp_raises() -> None:
    with pytest.raises(ValueError):
        infer_level_from_cp(100, 100, 100, 10, 10, 10, 500, observed_hp=-1)

