"""Static recommendations for move requirements and guidance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class MoveGuidance:
    """Guided settings for a Pokémon's raid moveset."""

    required_move: str
    needs_tm: bool
    note: str


_GUIDANCE: dict[str, MoveGuidance] = {
    "hydreigon": MoveGuidance(
        required_move="Brutal Swing",
        needs_tm=True,
        note="Needs Brutal Swing (Community Day / Elite TM).",
    ),
    "riolu": MoveGuidance(
        required_move="Aura Sphere",
        needs_tm=True,
        note="Lucario excels with Aura Sphere from Community Day / Elite TM.",
    ),
    "lucario": MoveGuidance(
        required_move="Aura Sphere",
        needs_tm=True,
        note="Ensure Aura Sphere is unlocked (Community Day / Elite TM).",
    ),
    "metagross": MoveGuidance(
        required_move="Meteor Mash",
        needs_tm=True,
        note="Meteor Mash is mandatory; acquire it via Community Day or Elite TM.",
    ),
    "beldum": MoveGuidance(
        required_move="Meteor Mash",
        needs_tm=True,
        note="Meteor Mash Metagross requires the Community Day move.",
    ),
    "rhyhorn": MoveGuidance(
        required_move="Rock Wrecker",
        needs_tm=True,
        note="Rock Wrecker is exclusive; use an Elite TM if you missed the event.",
    ),
    "rhyperior": MoveGuidance(
        required_move="Rock Wrecker",
        needs_tm=True,
        note="Rock Wrecker is exclusive; use an Elite TM if you missed the event.",
    ),
    "larvitar": MoveGuidance(
        required_move="Brutal Swing / Smack Down",
        needs_tm=True,
        note="Unlock Brutal Swing for Dark role; Smack Down Tyranitar also needs an Elite TM.",
    ),
    "tyranitar": MoveGuidance(
        required_move="Brutal Swing / Smack Down",
        needs_tm=True,
        note="Unlock Brutal Swing for Dark role; Smack Down Tyranitar also needs an Elite TM.",
    ),
    "blastoise": MoveGuidance(
        required_move="Hydro Cannon",
        needs_tm=True,
        note="Hydro Cannon is Community Day exclusive; TM or wait for reruns.",
    ),
    "venusaur": MoveGuidance(
        required_move="Frenzy Plant",
        needs_tm=True,
        note="Frenzy Plant is required for raid relevance; obtain via CD or Elite TM.",
    ),
    "treecko": MoveGuidance(
        required_move="Frenzy Plant",
        needs_tm=True,
        note="Frenzy Plant Sceptile needs Community Day or Elite TM.",
    ),
    "grovyle": MoveGuidance(
        required_move="Frenzy Plant",
        needs_tm=True,
        note="Frenzy Plant Sceptile needs Community Day or Elite TM.",
    ),
    "sceptile": MoveGuidance(
        required_move="Frenzy Plant",
        needs_tm=True,
        note="Frenzy Plant Sceptile needs Community Day or Elite TM.",
    ),
    "starly": MoveGuidance(
        required_move="Gust",
        needs_tm=True,
        note="Gust is a Community Day fast move; Elite TM if missing.",
    ),
    "staraptor": MoveGuidance(
        required_move="Gust",
        needs_tm=True,
        note="Gust is a Community Day fast move; Elite TM if missing.",
    ),
    "litten": MoveGuidance(
        required_move="Blast Burn",
        needs_tm=True,
        note="Blast Burn Incineroar requires Community Day / Elite TM.",
    ),
    "incineroar": MoveGuidance(
        required_move="Blast Burn",
        needs_tm=True,
        note="Blast Burn Incineroar requires Community Day / Elite TM.",
    ),
    "gastly": MoveGuidance(
        required_move="Shadow Claw / Lick",
        needs_tm=True,
        note="Legacy fast moves (Lick/Shadow Claw) boost Gengar; plan for Elite TM.",
    ),
    "haunter": MoveGuidance(
        required_move="Shadow Claw / Lick",
        needs_tm=True,
        note="Legacy fast moves (Lick/Shadow Claw) boost Gengar; plan for Elite TM.",
    ),
    "gengar": MoveGuidance(
        required_move="Shadow Claw / Lick",
        needs_tm=True,
        note="Legacy fast moves (Lick/Shadow Claw) boost Gengar; plan for Elite TM.",
    ),
    "cyndaquil": MoveGuidance(
        required_move="Blast Burn",
        needs_tm=True,
        note="Blast Burn Typhlosion is exclusive to Community Day / Elite TM.",
    ),
    "typhlosion": MoveGuidance(
        required_move="Blast Burn",
        needs_tm=True,
        note="Blast Burn Typhlosion is exclusive to Community Day / Elite TM.",
    ),
    "roggenrola": MoveGuidance(
        required_move="Meteor Beam",
        needs_tm=True,
        note="Meteor Beam was event-limited; use an Elite TM if you missed it.",
    ),
    "gigalith": MoveGuidance(
        required_move="Meteor Beam",
        needs_tm=True,
        note="Meteor Beam was event-limited; use an Elite TM if you missed it.",
    ),
}


def normalise_name(name: str) -> str:
    """Normalise a Pokémon label while keeping meaningful form descriptors."""

    cleaned = name.lower().strip()
    prefix_map = ("shadow ", "purified ", "mega ", "apex shadow ", "apex ")
    for prefix in prefix_map:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            break

    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.replace("’", "'")

    ignored_tokens = {
        "preferred",
        "form",
        "forme",
        "forms",
        "raid",
        "build",
        "team",
        "lucky",
        "hundo",
        "l40",
        "lvl40",
        "level40",
        "xl",
        "shadow",
        "mega",
    }

    import re

    form_tokens: list[str] = []
    for match in re.findall(r"\(([^)]+)\)", cleaned):
        tokens = [token for token in re.split(r"[\s/]+", match) if token]
        meaningful = [token for token in tokens if token not in ignored_tokens]
        if meaningful:
            form_tokens.extend(meaningful)
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)

    cleaned = cleaned.split("#", 1)[0]
    cleaned = cleaned.replace("'", "")

    base_tokens = [token for token in re.split(r"[^a-z0-9]+", cleaned) if token]
    slug_parts = base_tokens
    if form_tokens:
        slug_parts = base_tokens + [token for token in form_tokens if token]

    if not slug_parts:
        return ""

    return "-".join(slug_parts)


def get_move_guidance(name: str) -> MoveGuidance | None:
    """Return move guidance for *name* when available."""

    return _GUIDANCE.get(normalise_name(name))


__all__: Final = ["MoveGuidance", "get_move_guidance", "normalise_name"]
