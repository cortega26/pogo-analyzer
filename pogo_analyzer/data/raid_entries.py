"""Data structures and helpers backing the raid scoreboard dataset."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, fields
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any, Iterable, Mapping

from pogo_analyzer.scoring import calculate_iv_bonus, calculate_raid_score
from pogo_analyzer.scoring.metrics import SCORE_MAX, SCORE_MIN
from pogo_analyzer.tables import Row

IVSpread = tuple[int, int, int]


@dataclass(frozen=True)
class PokemonRaidEntry:
    """Descriptor for a single Pokémon entry on the raid scoreboard."""

    name: str
    ivs: IVSpread
    final_form: str = ""
    role: str = ""
    base: float = 70.0
    lucky: bool = False
    shadow: bool = False
    needs_tm: bool = False
    mega_now: bool = False
    mega_soon: bool = False
    notes: str = ""
    purified: bool = False
    best_buddy: bool = False

    def __post_init__(self) -> None:
        """Validate the supplied metadata so rows remain well-formed."""

        if not self.name or not self.name.strip():
            raise ValueError("PokemonRaidEntry.name must be a non-empty string.")

        if len(self.ivs) != 3:
            raise ValueError("PokemonRaidEntry.ivs must contain exactly three values.")

        for value in self.ivs:
            if not isinstance(value, int):
                raise TypeError("PokemonRaidEntry.ivs values must be integers.")
            if not 0 <= value <= 15:
                msg = "PokemonRaidEntry.ivs values must be between 0 and 15 inclusive."
                raise ValueError(msg)

        if not SCORE_MIN <= self.base <= SCORE_MAX:
            msg = (
                "PokemonRaidEntry.base must fall within the inclusive raid score "
                f"range [{SCORE_MIN}, {SCORE_MAX}]."
            )
            raise ValueError(msg)

    def formatted_name(self) -> str:
        """Return the display name with ``(lucky)``/``(shadow)`` suffixes."""

        suffix = ""
        if self.lucky:
            suffix += " (lucky)"
        if self.shadow:
            suffix += " (shadow)"
        if self.purified:
            suffix += " (purified)"
        if self.best_buddy:
            suffix += " (best buddy)"
        return f"{self.name}{suffix}"

    def iv_text(self) -> str:
        """Render the IV tuple in ``Atk/Def/Sta`` order."""

        attack_iv, defence_iv, stamina_iv = self.ivs
        return f"{attack_iv}/{defence_iv}/{stamina_iv}"

    def mega_text(self) -> str:
        """Return ``Yes``, ``Soon``, or ``No`` for the mega availability column."""

        if self.mega_now:
            return "Yes"
        if self.mega_soon:
            return "Soon"
        return "No"

    def move_text(self) -> str:
        """Return ``Yes`` when the Pokémon relies on a special move."""

        return "Yes" if self.needs_tm else "No"

    def to_row(self) -> Row:
        """Convert the dataclass into the row structure consumed by tables."""

        attack_iv, defence_iv, stamina_iv = self.ivs
        score = calculate_raid_score(
            self.base,
            calculate_iv_bonus(attack_iv, defence_iv, stamina_iv),
            lucky=self.lucky,
            needs_tm=self.needs_tm,
            mega_bonus_now=self.mega_now,
            mega_bonus_soon=self.mega_soon,
        )
        if self.purified:
            score += 1
        if self.best_buddy:
            score += 2
        score = max(SCORE_MIN, min(SCORE_MAX, round(score, 1)))
        extra_notes: list[str] = []
        if self.purified:
            extra_notes.append("Purified bonus applied.")
        if self.best_buddy:
            extra_notes.append("Best Buddy bonus applied.")
        notes = self.notes
        if extra_notes:
            joined = " ".join(extra_notes)
            notes = f"{notes} {joined}".strip()
        return {
            "Your Pokémon": self.formatted_name(),
            "IV (Atk/Def/Sta)": self.iv_text(),
            "Final Raid Form": self.final_form,
            "Primary Role": self.role,
            "Move Needs (CD/ETM?)": self.move_text(),
            "Mega Available": self.mega_text(),
            "Raid Score (1-100)": score,
            "Why it scores like this": notes,
        }

    def as_row(self) -> Row:
        """Backward-compatible alias for :meth:`to_row`."""

        return self.to_row()


_ENTRY_FIELD_NAMES = {field.name for field in fields(PokemonRaidEntry)}
_STRING_FIELDS = {"name", "final_form", "role", "notes"}
_BOOLEAN_FIELDS = {
    "lucky",
    "shadow",
    "needs_tm",
    "mega_now",
    "mega_soon",
    "purified",
    "best_buddy",
}


@cache
def _entry_row_items(entry: PokemonRaidEntry) -> tuple[tuple[str, object], ...]:
    """Return a cached tuple of row items for a raid entry."""

    row = entry.to_row()
    return tuple(row.items())


def build_entry_rows(entries: Sequence[PokemonRaidEntry]) -> list[Row]:
    """Convert entries to dictionaries ready for :class:`~tables.SimpleTable`."""

    return [dict(_entry_row_items(entry)) for entry in entries]


def build_rows(entries: Sequence[PokemonRaidEntry]) -> list[Row]:
    """Backward-compatible alias for :func:`build_entry_rows`."""

    return build_entry_rows(entries)



def _read_payload(path: Path | str | None) -> tuple[Mapping[str, Any], list[Any]]:
    """Return metadata and entry data loaded from JSON."""

    if path is None:
        resource = resources.files(__package__).joinpath("raid_entries.json")
        raw = resource.read_text(encoding="utf-8")
    else:
        raw = Path(path).read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - rarely triggered in tests.
        raise ValueError(f"Failed to parse raid entry JSON: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("Raid entry data must be a JSON object.")
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("Raid entry payload requires a 'metadata' object.")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Raid entry payload requires an 'entries' array.")
    return metadata, entries


def _parse_metadata(metadata: Mapping[str, Any]) -> set[str]:
    """Validate metadata and return the set of required field names."""

    schema_version = metadata.get("schema_version")
    if not isinstance(schema_version, int):
        raise ValueError("Raid entry metadata must include an integer 'schema_version'.")
    fields_metadata = metadata.get("fields")
    if not isinstance(fields_metadata, Mapping):
        raise ValueError("Raid entry metadata must include a 'fields' mapping.")
    metadata_fields = set(fields_metadata)
    missing = _ENTRY_FIELD_NAMES - metadata_fields
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(
            f"Raid entry metadata is missing definitions for fields: {missing_list}."
        )
    unsupported = metadata_fields - _ENTRY_FIELD_NAMES
    if unsupported:
        unsupported_list = ", ".join(sorted(unsupported))
        raise ValueError(
            "Raid entry metadata declares unsupported fields: "
            f"{unsupported_list}."
        )
    required_fields: set[str] = set()
    for field_name, descriptor in fields_metadata.items():
        if not isinstance(descriptor, Mapping):
            raise ValueError(
                f"Raid entry metadata for field '{field_name}' must be an object."
            )
        required_flag = descriptor.get("required", False)
        if not isinstance(required_flag, bool):
            raise ValueError(
                "Raid entry metadata for field '"
                f"{field_name}' has non-boolean 'required'."
            )
        if required_flag:
            required_fields.add(field_name)
    columns = metadata.get("columns")
    if columns is not None and not isinstance(columns, Mapping):
        raise ValueError("Raid entry metadata 'columns' must be an object when provided.")
    return required_fields


def _coerce_entry(
    raw_entry: Mapping[str, Any],
    index: int,
    required_fields: Iterable[str],
) -> PokemonRaidEntry:
    """Convert a JSON mapping into a :class:`PokemonRaidEntry`."""

    entry_name = raw_entry.get("name", f"#{index}")
    missing = [field for field in required_fields if field not in raw_entry]
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(
            f"Raid entry '{entry_name}' is missing required field(s): {missing_list}."
        )
    unknown = set(raw_entry) - _ENTRY_FIELD_NAMES
    if unknown:
        unknown_list = ", ".join(sorted(unknown))
        raise ValueError(
            f"Raid entry '{entry_name}' contains unknown field(s): {unknown_list}."
        )
    kwargs: dict[str, Any] = {}
    for field_name in _ENTRY_FIELD_NAMES:
        if field_name not in raw_entry:
            continue
        value = raw_entry[field_name]
        if field_name == "ivs":
            if not isinstance(value, (list, tuple)):
                raise TypeError(
                    f"Raid entry '{entry_name}' field 'ivs' must be a list of integers."
                )
            if len(value) != 3:
                raise ValueError(
                    f"Raid entry '{entry_name}' field 'ivs' must contain exactly three values."
                )
            if not all(isinstance(iv, int) and not isinstance(iv, bool) for iv in value):
                raise TypeError(
                    f"Raid entry '{entry_name}' field 'ivs' must contain integer values."
                )
            iv_tuple: IVSpread = (value[0], value[1], value[2])
            kwargs[field_name] = iv_tuple
        elif field_name == "base":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"Raid entry '{entry_name}' field 'base' must be a number."
                )
            kwargs[field_name] = float(value)
        elif field_name in _STRING_FIELDS:
            if not isinstance(value, str):
                raise TypeError(
                    f"Raid entry '{entry_name}' field '{field_name}' must be a string."
                )
            kwargs[field_name] = value
        elif field_name in _BOOLEAN_FIELDS:
            if not isinstance(value, bool):
                raise TypeError(
                    f"Raid entry '{entry_name}' field '{field_name}' must be a boolean."
                )
            kwargs[field_name] = value
        else:
            kwargs[field_name] = value
    try:
        return PokemonRaidEntry(**kwargs)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Raid entry '{entry_name}' is invalid: {exc}") from exc


def _load_entries_with_metadata(
    path: Path | str | None = None,
) -> tuple[list[PokemonRaidEntry], Mapping[str, Any]]:
    """Load entries (and metadata) from the packaged JSON file or a custom path."""

    metadata, raw_entries = _read_payload(path)
    required_fields = _parse_metadata(metadata)
    entries: list[PokemonRaidEntry] = []
    for index, item in enumerate(raw_entries):
        if not isinstance(item, Mapping):
            raise ValueError(
                f"Raid entry at index {index} must be an object; received {type(item).__name__}."
            )
        entries.append(_coerce_entry(item, index, required_fields))
    return entries, metadata


def load_raid_entries(path: Path | str | None = None) -> list[PokemonRaidEntry]:
    """Return raid entries parsed from ``path`` or the bundled dataset."""

    entries, _ = _load_entries_with_metadata(path)
    return entries


DEFAULT_RAID_ENTRIES, DEFAULT_RAID_ENTRY_METADATA = _load_entries_with_metadata()

RAID_ENTRIES = DEFAULT_RAID_ENTRIES

__all__ = [
    "DEFAULT_RAID_ENTRIES",
    "DEFAULT_RAID_ENTRY_METADATA",
    "IVSpread",
    "PokemonRaidEntry",
    "RAID_ENTRIES",
    "build_entry_rows",
    "build_rows",
    "load_raid_entries",
]
