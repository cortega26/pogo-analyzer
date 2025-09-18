"""Species base stats sourced from PvPoke's gamemaster."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Iterable, Iterator

from .move_guidance import normalise_name


@dataclass(frozen=True)
class BaseStats:
    """Base attack, defence, and stamina for a Pokémon species/form."""

    slug: str
    name: str | None
    dex: int
    attack: int
    defense: int
    stamina: int
    types: tuple[str, ...]
    tags: tuple[str, ...]
    default_ivs: dict[str, list[float]] | None
    family: dict[str, object] | str | None

    def as_tuple(self) -> tuple[int, int, int]:
        """Return ``(attack, defence, stamina)`` for convenience."""

        return self.attack, self.defense, self.stamina


class BaseStatsRepository:
    """In-memory index of :class:`BaseStats` keyed by multiple aliases."""

    def __init__(self, entries: Iterable[BaseStats]):
        self._entries = tuple(entries)
        aliases: dict[str, BaseStats] = {}
        for entry in self._entries:
            for key in _aliases_for_entry(entry):
                aliases.setdefault(key, entry)
        self._aliases = aliases

    def get(self, identifier: str) -> BaseStats:
        """Return base stats for *identifier* or raise :class:`KeyError`."""

        key = normalise_name(identifier)
        entry = self._aliases.get(key)
        if entry is None:
            raise KeyError(identifier)
        return entry

    def __contains__(self, identifier: str) -> bool:  # pragma: no cover - trivial
        try:
            self.get(identifier)
        except KeyError:
            return False
        return True

    def __iter__(self) -> Iterator[BaseStats]:  # pragma: no cover - rarely used
        yield from self._entries


def _aliases_for_entry(entry: BaseStats) -> set[str]:
    raw_slug = entry.slug.lower()
    candidates = {
        raw_slug,
        raw_slug.replace("_", "-"),
        raw_slug.replace("_", ""),
        raw_slug.replace("-", ""),
        normalise_name(entry.slug),
    }
    if entry.name:
        candidates.add(normalise_name(entry.name))
    if entry.dex:
        candidates.add(str(entry.dex))
        candidates.add(f"#{entry.dex}")
    for prefix in ("shadow_", "mega_", "purified_", "apex_", "galarian_", "alolan_", "hisuian_"):
        if raw_slug.startswith(prefix):
            trimmed = raw_slug[len(prefix) :]
            candidates.add(trimmed)
            candidates.add(trimmed.replace("_", "-"))
    if entry.family:
        family_value = entry.family.get('id') if isinstance(entry.family, dict) else entry.family
        if isinstance(family_value, str):
            candidates.add(normalise_name(family_value))
    return {candidate for candidate in candidates if candidate}


def load_base_stats(path: str | Path | None = None) -> BaseStatsRepository:
    """Load base stats from *path* or the bundled JSON payload."""

    if path is None:
        payload_path = resources.files(__package__).joinpath("base_stats.json")
        raw = payload_path.read_text(encoding="utf-8")
    else:
        payload_path = Path(path)
        raw = payload_path.read_text(encoding="utf-8")

    data = json.loads(raw)
    entries_data = data.get("entries")
    if not isinstance(entries_data, list):
        raise ValueError("Base stats payload must contain an 'entries' array.")

    entries: list[BaseStats] = []
    for item in entries_data:
        if not isinstance(item, dict):
            continue
        try:
            entry = BaseStats(
                slug=item["slug"],
                name=item.get("name"),
                dex=int(item.get("dex", 0)),
                attack=int(item["attack"]),
                defense=int(item["defense"]),
                stamina=int(item["stamina"]),
                types=tuple(item.get("types", [])),
                tags=tuple(item.get("tags", [])),
                default_ivs=item.get("defaultIVs"),
                family=item.get("family"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid base stats entry: {item}") from exc
        entries.append(entry)
    if not entries:
        raise ValueError("No valid base stats entries were loaded.")

    return BaseStatsRepository(entries)


@lru_cache(maxsize=1)
def load_default_base_stats() -> BaseStatsRepository:
    """Return the cached repository backed by the bundled dataset."""

    return load_base_stats()


__all__ = [
    "BaseStats",
    "BaseStatsRepository",
    "load_base_stats",
    "load_default_base_stats",
]
