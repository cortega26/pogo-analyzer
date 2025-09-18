"""Unit tests for the base stats repository."""

from __future__ import annotations

import pytest

from pogo_analyzer.data.base_stats import BaseStatsRepository, load_default_base_stats


@pytest.fixture(scope="module")
def base_stats_repo() -> BaseStatsRepository:
    return load_default_base_stats()


def test_base_stats_lookup_by_species_name(base_stats_repo: BaseStatsRepository) -> None:
    entry = base_stats_repo.get("Hydreigon")
    assert entry.slug == "hydreigon"
    assert (entry.attack, entry.defense, entry.stamina) == (256, 188, 211)


def test_base_stats_lookup_form_alias(base_stats_repo: BaseStatsRepository) -> None:
    entry = base_stats_repo.get("Giratina (Origin Forme)")
    assert entry.slug == "giratina_origin"
    assert entry.types == ("ghost", "dragon")


def test_base_stats_lookup_shadow_label(base_stats_repo: BaseStatsRepository) -> None:
    entry = base_stats_repo.get("Shadow Beldum")
    assert entry.slug == "beldum"
    assert entry.attack == 96


def test_base_stats_unknown_species_raises(base_stats_repo: BaseStatsRepository) -> None:
    with pytest.raises(KeyError):
        base_stats_repo.get("Missingno")
