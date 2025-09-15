"""Tools for building and managing Pokémon teams."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

from . import data_loader
from .analysis import analyze_pokemon

MemberData = Dict[str, Any]
TEAMS_FILE = Path(__file__).resolve().parents[2] / "data" / "teams.json"


def _normalize_ivs(ivs: Sequence[int]) -> List[int]:
    values = [int(v) for v in ivs]
    if len(values) != 3:
        raise ValueError("IVs must contain attack, defense, and stamina values")
    return values


def _normalize_member(entry: Mapping[str, Any]) -> MemberData:
    if "species" not in entry:
        raise ValueError("Team members must include a species name")
    if "ivs" not in entry:
        raise ValueError("Team members must include IV values")
    form = entry.get("form", "Normal")
    ivs = _normalize_ivs(entry["ivs"])
    level = float(entry.get("level", 1.0))
    member: MemberData = {
        "species": entry["species"],
        "form": form,
        "ivs": ivs,
        "level": level,
        "shadow": bool(entry.get("shadow", False)),
        "purified": bool(entry.get("purified", False)),
        "best_buddy": bool(entry.get("best_buddy", False)),
    }
    return member


def read_roster_data(path: Path | str = TEAMS_FILE) -> Dict[str, Any]:
    """Read the team roster data from ``path``.

    Missing files return an empty mapping. JSON parsing errors will be raised to
    signal corrupted data to the caller.
    """

    roster_path = Path(path)
    if not roster_path.exists():
        return {}
    text = roster_path.read_text().strip()
    if not text:
        return {}
    data = json.loads(text)
    if not isinstance(data, MutableMapping):
        raise ValueError("Roster data must be a mapping of team names to members")
    return dict(data)


def write_roster_data(data: Mapping[str, Any], path: Path | str = TEAMS_FILE) -> None:
    """Write the roster mapping to disk."""

    roster_path = Path(path)
    roster_path.parent.mkdir(parents=True, exist_ok=True)
    roster_path.write_text(json.dumps(dict(data), indent=2, sort_keys=True))


@dataclass
class Team:
    """A named collection of Pokémon.

    Members are stored as dictionaries containing the fields required to call
    :func:`analysis.analyze_pokemon`.
    """

    name: str
    members: List[MemberData] = field(default_factory=list)

    def add_member(
        self,
        species: str,
        *,
        form: str = "Normal",
        ivs: Sequence[int] = (0, 0, 0),
        level: float = 1.0,
        shadow: bool = False,
        purified: bool = False,
        best_buddy: bool = False,
    ) -> MemberData:
        member = _normalize_member(
            {
                "species": species,
                "form": form,
                "ivs": ivs,
                "level": level,
                "shadow": shadow,
                "purified": purified,
                "best_buddy": best_buddy,
            }
        )
        self.members.append(member)
        return member

    def analyze_members(self) -> List[Dict[str, Any]]:
        analyses: List[Dict[str, Any]] = []
        for member in self.members:
            analysis = analyze_pokemon(
                member["species"],
                member.get("form", "Normal"),
                tuple(member["ivs"]),
                member.get("level", 1.0),
                shadow=member.get("shadow", False),
                purified=member.get("purified", False),
                best_buddy=member.get("best_buddy", False),
            )
            analyses.append(analysis)
        return analyses

    def recommend_for_league(self, league: str) -> Dict[str, Any]:
        league_key = league.lower()
        if league_key not in data_loader.LEAGUE_CP_CAPS:
            raise ValueError(f"Unknown league '{league}'")
        analyses = self.analyze_members()
        if not analyses:
            raise ValueError("Cannot recommend from an empty team")
        best = max(
            analyses,
            key=lambda result: result["pvp"][league_key]["stat_product"],
        )
        return {
            "team": self.name,
            "league": league_key,
            "best_member": best["name"],
            "analysis": best,
            "members": analyses,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "members": [dict(member) for member in self.members]}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, name: Optional[str] = None) -> "Team":
        team_name = name or data.get("name")
        if not team_name:
            raise ValueError("Team name is required")
        members = [_normalize_member(member) for member in data.get("members", [])]
        return cls(name=team_name, members=members)


class Roster:
    """Collection of named teams backed by a JSON data file."""

    def __init__(self, teams: Optional[Mapping[str, Team]] = None, *, storage_path: Path | str = TEAMS_FILE):
        self._teams: Dict[str, Team] = {name: team for name, team in (teams or {}).items()}
        self._path = Path(storage_path)

    @classmethod
    def load(cls, path: Path | str = TEAMS_FILE) -> "Roster":
        raw = read_roster_data(path)
        teams = {name: Team.from_dict(data, name=name) for name, data in raw.items()}
        return cls(teams, storage_path=path)

    def save(self) -> None:
        write_roster_data({name: team.to_dict() for name, team in self._teams.items()}, self._path)

    def create_team(self, name: str) -> Team:
        if name in self._teams:
            raise ValueError(f"Team '{name}' already exists")
        team = Team(name)
        self._teams[name] = team
        self.save()
        return team

    def get_team(self, name: str) -> Team:
        try:
            return self._teams[name]
        except KeyError as exc:
            raise KeyError(f"Team '{name}' does not exist") from exc

    def add_member(
        self,
        team_name: str,
        *,
        species: str,
        form: str = "Normal",
        ivs: Sequence[int] = (0, 0, 0),
        level: float = 1.0,
        shadow: bool = False,
        purified: bool = False,
        best_buddy: bool = False,
    ) -> MemberData:
        team = self.get_team(team_name)
        member = team.add_member(
            species,
            form=form,
            ivs=ivs,
            level=level,
            shadow=shadow,
            purified=purified,
            best_buddy=best_buddy,
        )
        self.save()
        return member

    def recommend(self, team_name: str, league: str) -> Dict[str, Any]:
        team = self.get_team(team_name)
        return team.recommend_for_league(league)

    def to_dict(self) -> Dict[str, Any]:
        return {name: team.to_dict() for name, team in self._teams.items()}


__all__ = ["MemberData", "TEAMS_FILE", "Team", "Roster", "read_roster_data", "write_roster_data"]
