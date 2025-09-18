from __future__ import annotations

from pogo_analyzer.ui_helpers import pve_verdict, pvp_verdict
from pogo_analyzer.ui_helpers import pve_tier


def test_pvp_verdict_thresholds() -> None:
    assert pvp_verdict(0.90)[0] == "Top-tier"
    assert pvp_verdict(0.80)[0] == "Strong"
    assert pvp_verdict(0.66)[0].startswith("Niche")
    assert pvp_verdict(0.50)[0] == "Not recommended"


def test_pve_verdict_common_patterns() -> None:
    # Glass cannon
    label, _ = pve_verdict(16.5, 30.0)
    assert label == "Glass cannon"
    # Strong pick
    label, _ = pve_verdict(14.5, 45.0)
    assert label in {"Strong pick", "Top-tier raid attacker"}
    # High DPS + Decent TDO should be strong
    label, _ = pve_verdict(21.8, 55.0)
    assert label == "Strong pick"
    # Underwhelming
    assert pve_verdict(10.0, 20.0)[0] in {"Underwhelming", "Bulky but slow"}


def test_pve_tier_mapping() -> None:
    assert pve_tier(19.0, 75.0)[0] == "S"
    assert pve_tier(19.0, 50.0)[0] == "A"
    assert pve_tier(19.0, 30.0)[0] == "B"
    assert pve_tier(15.0, 50.0)[0] == "A"
    assert pve_tier(15.0, 46.0)[0] == "B"
    assert pve_tier(15.0, 30.0)[0] == "C"
    assert pve_tier(13.0, 46.0)[0] == "C"
    assert pve_tier(13.0, 30.0)[0] == "D"
    assert pve_tier(10.0, 46.0)[0] == "D"
    assert pve_tier(10.0, 20.0)[0] in {"E", "F"}
