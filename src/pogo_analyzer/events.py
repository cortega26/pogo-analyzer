"""Utilities for fetching and parsing temporary game events."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import URLError
from urllib.request import urlopen

DEFAULT_EVENT_FEED = os.environ.get("POGO_ANALYZER_EVENT_FEED", "")


def _parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp into a timezone-aware datetime."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch_event_data(source: Optional[str] = None) -> Dict[str, Any]:
    """Return the raw JSON payload for the configured event feed.

    The feed can be provided via an explicit ``source`` argument, an environment
    variable (``POGO_ANALYZER_EVENT_FEED``), or will default to an empty
    collection when no feed is configured. ``source`` may point to a HTTP(S)
    endpoint or a local JSON file.
    """

    src = source or DEFAULT_EVENT_FEED
    if not src:
        return {"events": []}

    try:
        if src.startswith(("http://", "https://")):
            with urlopen(src, timeout=5) as response:  # nosec - controlled input
                payload = response.read().decode("utf-8")
            data = json.loads(payload)
        else:
            data = json.loads(Path(src).read_text())
    except FileNotFoundError:
        return {"events": []}
    except URLError:
        return {"events": []}

    if isinstance(data, list):
        return {"events": data}
    if isinstance(data, dict):
        events = data.get("events")
        if events is None:
            raise ValueError("Event feed is missing an 'events' key")
        if not isinstance(events, list):
            raise ValueError("The 'events' entry must be a list")
        return {"events": events}
    raise ValueError("Unsupported event feed structure")


def _normalize_moves(raw_moves: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, List[str]]]]:
    """Normalize move modifiers into a species/form keyed mapping."""

    normalized: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
    for species, forms in raw_moves.items():
        if not isinstance(forms, dict):
            continue
        species_entry: Dict[str, Dict[str, List[str]]] = {}
        for form, move_data in forms.items():
            if not isinstance(move_data, dict):
                continue
            fast = move_data.get("fast", [])
            charged = move_data.get("charged", [])
            species_entry[form] = {
                "fast": list(fast),
                "charged": list(charged),
            }
        if species_entry:
            normalized[species] = species_entry
    return normalized


def _normalize_cp_caps(raw_caps: Dict[str, Any]) -> Dict[str, int]:
    """Normalize CP cap overrides into integer values."""

    caps: Dict[str, int] = {}
    for league, value in raw_caps.items():
        try:
            caps[league] = int(value)
        except (TypeError, ValueError):
            continue
    return caps


def parse_events(raw_events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert raw event dictionaries into a normalized structure."""

    events: List[Dict[str, Any]] = []
    for entry in raw_events:
        try:
            start = _parse_timestamp(entry["start"])
            end = _parse_timestamp(entry["end"])
        except (KeyError, ValueError):
            continue
        modifiers = entry.get("modifiers", {})
        moves = _normalize_moves(modifiers.get("moves", {}))
        cp_caps = _normalize_cp_caps(modifiers.get("cp_caps", {}))
        events.append(
            {
                "name": entry.get("name", "Unnamed Event"),
                "start": start,
                "end": end,
                "modifiers": {
                    "moves": moves,
                    "cp_caps": cp_caps,
                },
            }
        )
    return events


def get_active_modifiers(
    *, reference: Optional[datetime] = None, source: Optional[str] = None
) -> Dict[str, Any]:
    """Return combined modifiers for events active at ``reference`` time."""

    payload = fetch_event_data(source)
    events = parse_events(payload.get("events", []))

    if reference is None:
        now = datetime.now(timezone.utc)
    else:
        now = reference if reference.tzinfo else reference.replace(tzinfo=timezone.utc)
        now = now.astimezone(timezone.utc)

    summary: Dict[str, Any] = {"active_events": [], "moves": {}, "cp_caps": {}}

    for event in events:
        if event["start"] <= now <= event["end"]:
            summary["active_events"].append(event["name"])
            for league, cap in event["modifiers"]["cp_caps"].items():
                summary["cp_caps"][league] = {"value": cap, "event": event["name"]}
            for species, forms in event["modifiers"]["moves"].items():
                species_entry = summary["moves"].setdefault(species, {})
                for form, move_data in forms.items():
                    species_entry[form] = {
                        "fast": list(move_data.get("fast", [])),
                        "charged": list(move_data.get("charged", [])),
                        "event": event["name"],
                    }

    return summary
