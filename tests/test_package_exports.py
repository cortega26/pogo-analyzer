"""Tests covering public package re-exports."""

from __future__ import annotations

from pogo_analyzer import (
    compute_pve_score,
    compute_pvp_score,
    damage_per_hit,
    effective_stats,
    infer_level_from_cp,
)
from pogo_analyzer.formulas import (
    damage_per_hit as formulas_damage_per_hit,
    effective_stats as formulas_effective_stats,
    infer_level_from_cp as formulas_infer_level_from_cp,
)
from pogo_analyzer.pve import compute_pve_score as module_compute_pve_score
from pogo_analyzer.pvp import compute_pvp_score as module_compute_pvp_score


def test_formulas_functions_are_reexported() -> None:
    """Package exports should reference the underlying formula helpers."""

    assert infer_level_from_cp is formulas_infer_level_from_cp
    assert effective_stats is formulas_effective_stats
    assert damage_per_hit is formulas_damage_per_hit


def test_pve_function_is_reexported() -> None:
    """Compute PvE score should be provided via the package namespace."""

    assert compute_pve_score is module_compute_pve_score


def test_pvp_function_is_reexported() -> None:
    """Compute PvP score should be provided via the package namespace."""

    assert compute_pvp_score is module_compute_pvp_score

