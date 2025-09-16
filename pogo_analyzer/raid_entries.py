"""Backward-compatible re-export of raid entry helpers.

This shim allows existing imports like ``from pogo_analyzer.raid_entries`` to
continue working after the package restructuring in vNext.
"""

from __future__ import annotations

from .data.raid_entries import (
    DEFAULT_RAID_ENTRIES,
    PokemonRaidEntry,
    build_entry_rows,
    build_rows,
)

# Public aliases preserved for compatibility with pre-refactor code.
RAID_ENTRIES = DEFAULT_RAID_ENTRIES

__all__ = [
    "DEFAULT_RAID_ENTRIES",
    "PokemonRaidEntry",
    "RAID_ENTRIES",
    "build_entry_rows",
    "build_rows",
]
