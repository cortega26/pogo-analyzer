import json
from datetime import datetime, timezone

from pogo_analyzer import events


def _write_event_feed(tmp_path):
    payload = {
        "events": [
            {
                "name": "Great League Remix",
                "start": "2023-01-01T00:00:00Z",
                "end": "2023-01-07T23:59:59Z",
                "modifiers": {
                    "moves": {
                        "Bulbasaur": {
                            "Normal": {
                                "fast": ["Vine Whip"],
                                "charged": ["Seed Bomb"],
                            }
                        }
                    },
                    "cp_caps": {"great": 1400},
                },
            }
        ]
    }
    path = tmp_path / "events.json"
    path.write_text(json.dumps(payload))
    return path, payload


def test_fetch_event_data_from_file(tmp_path):
    path, payload = _write_event_feed(tmp_path)
    loaded = events.fetch_event_data(str(path))
    assert loaded == payload


def test_get_active_modifiers(tmp_path):
    path, _ = _write_event_feed(tmp_path)
    reference = datetime(2023, 1, 5, tzinfo=timezone.utc)
    modifiers = events.get_active_modifiers(reference=reference, source=str(path))

    assert modifiers["active_events"] == ["Great League Remix"]
    cp_caps = modifiers["cp_caps"]
    assert cp_caps["great"]["value"] == 1400
    assert cp_caps["great"]["event"] == "Great League Remix"

    moves = modifiers["moves"]["Bulbasaur"]["Normal"]
    assert moves["fast"] == ["Vine Whip"]
    assert moves["charged"] == ["Seed Bomb"]
    assert moves["event"] == "Great League Remix"

    inactive = events.get_active_modifiers(
        reference=datetime(2023, 2, 1, tzinfo=timezone.utc),
        source=str(path),
    )
    assert inactive == {"active_events": [], "moves": {}, "cp_caps": {}}
