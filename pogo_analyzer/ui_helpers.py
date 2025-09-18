from __future__ import annotations

from typing import Tuple


def pvp_verdict(score: float) -> Tuple[str, str]:
    """Return a friendly verdict for a PvP score in [0,1].

    Returns (label, advice).
    """

    if score >= 0.85:
        return (
            "Top-tier",
            "Meta staple; build and use confidently (with the right moves).",
        )
    if score >= 0.75:
        return (
            "Strong",
            "Very competitive; shines with proper team support and matchups.",
        )
    if score >= 0.65:
        return (
            "Niche/solid",
            "Usable in the right cups or roles; expect tradeoffs.",
        )
    return (
        "Not recommended",
        "Struggles against common meta picks; consider alternatives unless favorite.",
    )


def pve_verdict(dps: float, tdo: float) -> Tuple[str, str]:
    """Return a friendly verdict for PvE DPS/TDO.

    Uses coarse thresholds; intended as guidance, not absolute ranks.
    Returns (label, advice).
    """

    # Coarse bands — scenario dependent but useful for first-glance guidance
    if dps >= 16.0:
        dps_band = "High"
    elif dps >= 14.0:
        dps_band = "Good"
    elif dps >= 12.0:
        dps_band = "OK"
    else:
        dps_band = "Low"

    if tdo >= 60.0:
        tdo_band = "High"
    elif tdo >= 40.0:
        tdo_band = "Decent"
    else:
        tdo_band = "Low"

    if dps_band == "High" and tdo_band == "High":
        return ("Top-tier raid attacker", "Excellent balance of damage and durability; worth powering up.")
    # High DPS with Decent durability is a very strong practical attacker
    if dps_band == "High" and tdo_band == "Decent":
        return ("Strong pick", "Reliable performance in many raids; a safe build.")
    if dps_band in {"High", "Good", "OK"} and tdo_band == "Low":
        return ("Glass cannon", "Huge damage but faints fast; great when dodging or in favorable matchups.")
    if dps_band == "Low" and tdo_band in {"High", "Decent"}:
        return ("Bulky but slow", "Survivable but low output; consider stronger attackers if available.")
    if dps_band == "Good" and tdo_band in {"Decent", "High"}:
        return ("Strong pick", "Reliable performance in many raids; a safe build.")
    if dps_band == "OK" and tdo_band == "Decent":
        return ("Situational", "Usable with the right typing advantage; not a priority build.")
    return ("Underwhelming", "Limited raid impact in typical settings; low priority.")


def _pve_bands(dps: float, tdo: float) -> Tuple[str, str]:
    if dps >= 18.0:
        dps_band = "High"
    elif dps >= 14.0:
        dps_band = "Good"
    elif dps >= 12.0:
        dps_band = "OK"
    else:
        dps_band = "Low"

    if tdo >= 70.0:
        tdo_band = "High"
    elif tdo >= 45.0:
        tdo_band = "Decent"
    else:
        tdo_band = "Low"
    return dps_band, tdo_band


def pve_tier(dps: float, tdo: float) -> Tuple[str, str]:
    """Return (letter tier, action chip) for PvE.

    S/A/B => Build, C/D => Consider, E/F => Skip.
    """

    dps_band, tdo_band = _pve_bands(dps, tdo)
    # Tier mapping by bands
    if dps_band == "High" and tdo_band == "High":
        letter = "S"
    elif dps_band == "High" and tdo_band == "Decent":
        letter = "A"
    elif dps_band == "High" and tdo_band == "Low":
        letter = "B"
    elif dps_band == "Good" and tdo_band == "High":
        letter = "A"
    elif dps_band == "Good" and tdo_band == "Decent":
        # Upper end of Decent (>=50) is closer to A; lower end is B
        letter = "A" if tdo >= 50.0 else "B"
    elif dps_band == "Good" and tdo_band == "Low":
        letter = "C"
    elif dps_band == "OK" and tdo_band == "Decent":
        letter = "C"
    elif dps_band == "OK" and tdo_band == "Low":
        letter = "D"
    elif dps_band == "Low" and tdo_band in {"High", "Decent"}:
        letter = "D"
    elif dps_band == "Low" and tdo_band == "Low":
        letter = "E"
    else:
        letter = "F"

    action = "Build" if letter in {"S", "A", "B"} else ("Consider" if letter in {"C", "D"} else "Skip")
    return letter, action


__all__ = ["pvp_verdict", "pve_verdict", "pve_tier"]
