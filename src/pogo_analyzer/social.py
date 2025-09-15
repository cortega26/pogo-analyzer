"""Utilities for sharing raid results and maintaining a local leaderboard."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

LEADERBOARD_FILE = Path(__file__).resolve().parents[2] / "data" / "leaderboard.json"
SESSION_FILE = Path(__file__).resolve().parents[2] / "data" / "leaderboard_session.json"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    text = path.read_text().strip()
    if not text:
        return None
    return json.loads(text)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def login(username: str, *, session_path: Path | str = SESSION_FILE) -> str:
    """Persist the active username for future submissions."""

    if not isinstance(username, str):
        raise ValueError("Username must be a string")
    normalized = username.strip()
    if not normalized:
        raise ValueError("Username cannot be empty")
    path = Path(session_path)
    _write_json(path, {"user": normalized})
    return normalized


def logout(*, session_path: Path | str = SESSION_FILE) -> None:
    """Clear any active login session."""

    path = Path(session_path)
    if path.exists():
        path.unlink()


def get_current_user(*, session_path: Path | str = SESSION_FILE) -> Optional[str]:
    path = Path(session_path)
    data = _load_json(path)
    if not isinstance(data, Mapping):
        return None
    user = data.get("user")
    if isinstance(user, str) and user.strip():
        return user.strip()
    return None


def share_results(result: Mapping[str, Any], platform: str) -> str:
    """Create a platform-appropriate share string from a result mapping."""

    platform_key = platform.lower()
    title = str(result.get("title", "Results"))
    share_url = result.get("share_url")
    entries: List[Dict[str, Any]] = []
    for entry in result.get("top_entries", []):
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name", "Unknown"))
        form = entry.get("form")
        form_text = str(form) if isinstance(form, str) else ""
        score_value = entry.get("score", 0.0)
        try:
            score = float(score_value)
        except (TypeError, ValueError):
            score = 0.0
        tier = entry.get("tier")
        tier_text = str(tier) if isinstance(tier, str) else ""
        entries.append({
            "name": name,
            "form": form_text,
            "score": score,
            "tier": tier_text,
        })

    if platform_key == "twitter":
        summary_bits = []
        for idx, entry in enumerate(entries[:3], 1):
            label = entry["name"]
            if entry["form"]:
                label += f" ({entry['form']})"
            summary_bits.append(f"{idx}. {label} {entry['score']:.1f}")
        summary = f"{title}: " + "; ".join(summary_bits) if summary_bits else title
        link_suffix = f" {share_url}" if share_url else ""
        limit = 280 - len(link_suffix)
        trimmed = summary if len(summary) <= limit else summary[: max(limit - 3, 0)].rstrip() + "..."
        return trimmed + link_suffix

    if platform_key == "discord":
        lines = [f"**{title}**"]
        if share_url:
            lines.append(str(share_url))
        if entries:
            lines.append("```")
            for idx, entry in enumerate(entries, 1):
                label = entry["name"]
                if entry["form"]:
                    label += f" / {entry['form']}"
                lines.append(f"{idx:>2}. {label:<32} {entry['score']:>5.1f} {entry['tier']}")
            lines.append("```")
        return "\n".join(lines)

    if platform_key == "reddit":
        lines = [f"## {title}"]
        if share_url:
            lines.append(f"[View chart]({share_url})")
        for idx, entry in enumerate(entries, 1):
            label = entry["name"]
            if entry["form"]:
                label += f" ({entry['form']})"
            tier_text = f" ({entry['tier']})" if entry['tier'] else ""
            lines.append(f"{idx}. **{label}** – {entry['score']:.1f}{tier_text}")
        return "\n".join(lines)

    raise ValueError(f"Unsupported platform '{platform}'")


def load_leaderboard(*, leaderboard_path: Path | str = LEADERBOARD_FILE) -> List[Dict[str, Any]]:
    """Return the stored leaderboard entries sorted by score."""

    path = Path(leaderboard_path)
    raw = _load_json(path)
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("Leaderboard data must be a list of entries")
    entries: List[Dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise ValueError("Leaderboard entries must be mappings")
        user = entry.get("user")
        if not isinstance(user, str) or not user.strip():
            continue
        score_value = entry.get("score", 0.0)
        try:
            score = float(score_value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(score):
            continue
        label = entry.get("label") if isinstance(entry.get("label"), str) else None
        details = entry.get("details") if isinstance(entry.get("details"), str) else None
        timestamp = entry.get("timestamp") if isinstance(entry.get("timestamp"), str) else None
        entries.append({
            "user": user.strip(),
            "score": round(score, 2),
            "label": label,
            "details": details,
            "timestamp": timestamp,
        })
    entries.sort(key=lambda item: item["score"], reverse=True)
    return entries


def record_score(
    score: float,
    *,
    label: str | None = None,
    details: str | None = None,
    username: str | None = None,
    leaderboard_path: Path | str = LEADERBOARD_FILE,
    session_path: Path | str = SESSION_FILE,
    max_entries: int = 100,
) -> Dict[str, Any]:
    """Store a score for the active or provided user."""

    try:
        value = float(score)
    except (TypeError, ValueError) as exc:
        raise ValueError("Score must be numeric") from exc
    if not math.isfinite(value):
        raise ValueError("Score must be a finite number")

    user = username or get_current_user(session_path=session_path)
    if not user:
        raise ValueError("Login required to record scores")

    normalized_label = (
        label.strip() if isinstance(label, str) and label.strip() else "Raid Score"
    )
    detail_text = details.strip() if isinstance(details, str) and details.strip() else None
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    entry = {
        "user": user,
        "score": round(value, 2),
        "label": normalized_label,
        "details": detail_text,
        "timestamp": timestamp,
    }

    path = Path(leaderboard_path)
    leaderboard = load_leaderboard(leaderboard_path=path)
    leaderboard.append(entry)
    leaderboard.sort(key=lambda item: item["score"], reverse=True)
    if max_entries > 0:
        leaderboard = leaderboard[:max_entries]
    _write_json(path, leaderboard)
    return entry


__all__ = [
    "LEADERBOARD_FILE",
    "SESSION_FILE",
    "login",
    "logout",
    "get_current_user",
    "share_results",
    "load_leaderboard",
    "record_score",
]
