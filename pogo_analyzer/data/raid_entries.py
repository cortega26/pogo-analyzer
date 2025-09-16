"""Data structures and helpers backing the raid scoreboard dataset."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

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
        return {
            "Your Pokémon": self.formatted_name(),
            "IV (Atk/Def/Sta)": self.iv_text(),
            "Final Raid Form": self.final_form,
            "Primary Role": self.role,
            "Move Needs (CD/ETM?)": self.move_text(),
            "Mega Available": self.mega_text(),
            "Raid Score (1-100)": calculate_raid_score(
                self.base,
                calculate_iv_bonus(attack_iv, defence_iv, stamina_iv),
                lucky=self.lucky,
                needs_tm=self.needs_tm,
                mega_bonus_now=self.mega_now,
                mega_bonus_soon=self.mega_soon,
            ),
            "Why it scores like this": self.notes,
        }

    def as_row(self) -> Row:
        """Backward-compatible alias for :meth:`to_row`."""

        return self.to_row()


def build_entry_rows(entries: Sequence[PokemonRaidEntry]) -> list[Row]:
    """Convert entries to dictionaries ready for :class:`~tables.SimpleTable`."""

    return [entry.to_row() for entry in entries]


def build_rows(entries: Sequence[PokemonRaidEntry]) -> list[Row]:
    """Backward-compatible alias for :func:`build_entry_rows`."""

    return build_entry_rows(entries)


DEFAULT_RAID_ENTRIES: list[PokemonRaidEntry] = [
    PokemonRaidEntry(
        "Snover",
        (14, 12, 14),
        final_form="Abomasnow / Mega Abomasnow",
        role="Ice (mega support)",
        base=80,
        mega_now=True,
        notes="Mega Abomasnow is a strong Ice/Grass team booster; regular Abomasnow is serviceable but not top DPS.",
    ),
    PokemonRaidEntry(
        "Riolu #1",
        (14, 12, 13),
        final_form="Lucario",
        role="Fighting DPS",
        base=89,
        needs_tm=True,
        notes="Lucario with Aura Sphere is top-tier Fighting; may require event/Elite TM for optimal moves.",
    ),
    PokemonRaidEntry(
        "Riolu #2",
        (13, 15, 12),
        final_form="Lucario",
        role="Fighting DPS",
        base=89,
        needs_tm=True,
        notes="Same as above — excellent attacker with the right moves.",
    ),
    PokemonRaidEntry(
        "Numel",
        (15, 13, 11),
        final_form="Camerupt / Mega Camerupt",
        role="Fire/Ground (mega support)",
        base=76,
        mega_soon=True,
        notes="Regular Camerupt is weak; Mega Camerupt debut is imminent and mainly useful as a lobby booster.",
    ),
    PokemonRaidEntry(
        "Exeggutor",
        (15, 13, 13),
        final_form="Exeggutor",
        role="Grass/Psychic (budget)",
        base=70,
        lucky=True,
        notes="Outclassed by modern Grass/Psychic attackers; Lucky makes it cheap if you need filler.",
    ),
    PokemonRaidEntry(
        "Lopunny",
        (15, 13, 14),
        final_form="Mega Lopunny",
        role="Fighting mega support",
        base=78,
        mega_now=True,
        notes="Personal DPS is middling, but Mega boosts Fighting/Normal teams.",
    ),
    PokemonRaidEntry(
        "Starly",
        (14, 12, 15),
        final_form="Staraptor (Gust)",
        role="Flying DPS (budget)",
        base=77,
        lucky=True,
        needs_tm=True,
        notes="Gust is CD-only; with Gust it's a solid budget flier.",
    ),
    PokemonRaidEntry(
        "Flabebe (lucky)",
        (14, 13, 15),
        final_form="Florges",
        role="Fairy (low DPS)",
        base=58,
        lucky=True,
        notes="Florges has low raid DPS; mainly collection/PvP.",
    ),
    PokemonRaidEntry(
        "Flabebe #2",
        (15, 11, 11),
        final_form="Florges",
        role="Fairy (low DPS)",
        base=58,
        notes="Same as above.",
    ),
    PokemonRaidEntry(
        "Flabebe #3",
        (15, 13, 15),
        final_form="Florges",
        role="Fairy (low DPS)",
        base=58,
        notes="Same as above.",
    ),
    PokemonRaidEntry(
        "Flabebe #4",
        (15, 13, 15),
        final_form="Florges",
        role="Fairy (low DPS)",
        base=58,
        notes="Same as above.",
    ),
    PokemonRaidEntry(
        "Litten",
        (15, 10, 15),
        final_form="Incineroar (Blast Burn)",
        role="Fire DPS (mid)",
        base=78,
        needs_tm=True,
        notes="CD move Blast Burn needed; still behind top Fire like Reshiram/Blaziken/Chandelure.",
    ),
]

# Additional entries appended below to keep file manageable when editing blocks.
DEFAULT_RAID_ENTRIES += [
    PokemonRaidEntry(
        f"Heracross #{index}",
        ivs,
        final_form="Mega Heracross",
        role="Bug/Fighting (mega & DPS)",
        base=90,
        mega_now=True,
        notes="Mega Heracross is one of the strongest Bug attackers and solid Fighting mega.",
    )
    for index, ivs in enumerate(
        [(13, 11, 5), (14, 0, 10), (10, 9, 5), (12, 8, 11), (13, 8, 14)],
        1,
    )
]

DEFAULT_RAID_ENTRIES += [
    PokemonRaidEntry(
        "Shadow Tyrunt",
        (14, 15, 5),
        final_form="Shadow Tyrantrum",
        role="Rock/Dragon DPS (niche)",
        base=80,
        shadow=True,
        notes="Fun and strong on paper, but still behind top Rock/Dragon specialists in most raids.",
    ),
    PokemonRaidEntry(
        "Beldum",
        (15, 9, 4),
        final_form="Metagross (Meteor Mash)",
        role="Steel DPS (top)",
        base=90,
        needs_tm=True,
        notes="Meteor Mash is mandatory; top Steel attacker when built.",
    ),
    PokemonRaidEntry(
        "Electabuzz",
        (15, 10, 3),
        final_form="Electivire",
        role="Electric DPS (good)",
        base=82,
        notes="Strong budget Electric; behind Legendaries and Shadows but still very usable.",
    ),
    PokemonRaidEntry(
        "Gurdurr",
        (12, 6, 14),
        final_form="Conkeldurr",
        role="Fighting DPS (top non-mega)",
        base=86,
        notes="Conkeldurr is a top non-mega Fighting attacker.",
    ),
    PokemonRaidEntry(
        "Crawdaunt",
        (15, 13, 15),
        final_form="Crawdaunt",
        role="Water/Dark (spice)",
        base=60,
        lucky=True,
        notes="Glass cannon, outclassed by most Water/Dark specialists.",
    ),
    PokemonRaidEntry(
        "Shadow Magnemite",
        (11, 6, 10),
        final_form="Shadow Magnezone",
        role="Electric DPS (top non-legend)",
        base=88,
        shadow=True,
        notes="Shadow Magnezone is among the best non-legend Electric attackers.",
    ),
    PokemonRaidEntry(
        "Shadow Gastly",
        (9, 11, 15),
        final_form="Shadow Gengar",
        role="Ghost DPS (apex glass cannon)",
        base=93,
        shadow=True,
        needs_tm=True,
        notes="Shadow Gengar has elite DPS; benefits from legacy Lick/Shadow Ball.",
    ),
    PokemonRaidEntry(
        "Treecko",
        (14, 13, 10),
        final_form="Sceptile (Frenzy Plant) / Mega Sceptile",
        role="Grass DPS (top w/ Mega)",
        base=88,
        needs_tm=True,
        mega_now=True,
        notes="Frenzy Plant Sceptile is excellent; Mega Sceptile is the best Grass mega.",
    ),
    PokemonRaidEntry(
        "Arcanine",
        (15, 12, 10),
        final_form="Arcanine",
        role="Fire DPS (mid)",
        base=72,
        notes="Usable but far behind top Fire options.",
    ),
    PokemonRaidEntry(
        "Shadow Kirlia",
        (11, 11, 11),
        final_form="Shadow Gardevoir",
        role="Fairy DPS (top non-mega)",
        base=88,
        shadow=True,
        notes="Shadow Gardevoir is a top non-mega Fairy attacker; consider Gardevoir over Gallade for raids.",
    ),
    PokemonRaidEntry(
        "Drilbur",
        (14, 15, 14),
        final_form="Excadrill",
        role="Ground DPS (top non-legend)",
        base=86,
        lucky=True,
        notes="Excadrill has great DPS and resistances; lucky makes it cheap.",
    ),
    PokemonRaidEntry(
        "Grovyle",
        (15, 12, 13),
        final_form="Sceptile (Frenzy Plant) / Mega Sceptile",
        role="Grass DPS",
        base=88,
        needs_tm=True,
        mega_now=True,
        notes="Same as Treecko — pick your better IV to evolve.",
    ),
    PokemonRaidEntry(
        "Alakazam",
        (14, 13, 15),
        final_form="Alakazam / Mega Alakazam",
        role="Psychic DPS",
        base=80,
        mega_now=True,
        notes="As a non-mega it's okay; Mega Alakazam is a strong Psychic mega booster.",
    ),
    PokemonRaidEntry(
        "Drowzee",
        (14, 15, 13),
        final_form="Hypno",
        role="Psychic (low DPS)",
        base=55,
        lucky=True,
        notes="Not raid-relevant; mostly PvP/collection.",
    ),
    PokemonRaidEntry(
        "Scyther",
        (12, 15, 14),
        final_form="Scizor / Mega Scizor",
        role="Bug/Steel (mega support)",
        base=82,
        mega_now=True,
        notes="Scizor is mid for raids; Mega Scizor is a handy Bug/Steel booster.",
    ),
    PokemonRaidEntry(
        "Hariyama",
        (14, 15, 12),
        final_form="Hariyama",
        role="Fighting DPS (budget)",
        base=80,
        notes="Solid budget Fighter; outclassed by Machamp/Conkeldurr/Lucario.",
    ),
    PokemonRaidEntry(
        "Blastoise",
        (15, 14, 14),
        final_form="Blastoise / Mega Blastoise",
        role="Water (mega support)",
        base=82,
        lucky=True,
        needs_tm=True,
        mega_now=True,
        notes="Hydro Cannon needed for non-mega; Mega Blastoise is a strong Water mega.",
    ),
    PokemonRaidEntry(
        "Machamp",
        (15, 13, 14),
        final_form="Machamp",
        role="Fighting DPS (top non-shadow)",
        base=84,
        lucky=True,
        notes="Still a top non-legend Fighter with Counter/Dynamic Punch.",
    ),
    PokemonRaidEntry(
        "Shadow Drilbur",
        (14, 4, 15),
        final_form="Shadow Excadrill",
        role="Ground DPS (apex)",
        base=92,
        shadow=True,
        notes="Shadow Excadrill is among the best Ground DPS options; frailer but hits very hard.",
    ),
    PokemonRaidEntry(
        "Gengar (lucky)",
        (15, 13, 12),
        final_form="Gengar / Mega Gengar",
        role="Ghost DPS (high)",
        base=82,
        lucky=True,
        needs_tm=True,
        mega_now=True,
        notes="Great non-shadow DPS; can Mega for top-tier boosts.",
    ),
    PokemonRaidEntry(
        "Gengar (hundo)",
        (15, 15, 15),
        final_form="Gengar / Mega Gengar",
        role="Ghost DPS (high)",
        base=85,
        needs_tm=True,
        mega_now=True,
        notes="Perfect IVs; outstanding Mega candidate.",
    ),
    PokemonRaidEntry(
        "Venusaur",
        (15, 14, 15),
        final_form="Venusaur / Mega Venusaur",
        role="Grass DPS (good)",
        base=83,
        needs_tm=True,
        mega_now=True,
        notes="Frenzy Plant Venusaur is solid; Mega Venusaur offers bulky Grass mega support.",
    ),
    PokemonRaidEntry(
        "Rhyhorn",
        (13, 13, 15),
        final_form="Rhyperior (Rock Wrecker)",
        role="Rock DPS (top TDO)",
        base=88,
        needs_tm=True,
        notes="Rock Wrecker is mandatory; elite TDO and flexible Ground coverage.",
    ),
    PokemonRaidEntry(
        "Gyarados",
        (14, 13, 15),
        final_form="Gyarados / Mega Gyarados",
        role="Water/Dark (mega support)",
        base=82,
        lucky=True,
        mega_now=True,
        notes="As a mega it's a great Dark/Water booster; non-mega is decent but outclassed.",
    ),
    PokemonRaidEntry(
        "Larvitar #1",
        (15, 12, 13),
        final_form="Tyranitar (Brutal Swing) / Mega Tyranitar",
        role="Dark/Rock DPS",
        base=86,
        needs_tm=True,
        mega_now=True,
        notes="Brutal Swing makes Dark TTar great; Smack Down needs ETM for Rock role; Mega Tyranitar is elite.",
    ),
    PokemonRaidEntry(
        "Larvitar #2",
        (15, 15, 10),
        final_form="Tyranitar (Brutal Swing) / Mega Tyranitar",
        role="Dark/Rock DPS",
        base=86,
        needs_tm=True,
        mega_now=True,
        notes="Slightly better bulk; same notes as above.",
    ),
    PokemonRaidEntry(
        "Shadow Machoke",
        (13, 12, 7),
        final_form="Shadow Machamp",
        role="Fighting DPS (apex non-mega)",
        base=90,
        shadow=True,
        notes="Shadow Machamp is one of the best Fighters; very high DPS.",
    ),
    PokemonRaidEntry(
        "Haunter",
        (14, 14, 15),
        final_form="Gengar / Mega Gengar",
        role="Ghost DPS (high)",
        base=84,
        needs_tm=True,
        mega_now=True,
        notes="Great IVs; evolve for another strong Gengar or Mega candidate.",
    ),
    PokemonRaidEntry(
        "Shadow Cyndaquil",
        (13, 0, 12),
        final_form="Shadow Typhlosion (Blast Burn)",
        role="Fire DPS (high)",
        base=87,
        shadow=True,
        needs_tm=True,
        notes="With Blast Burn it's a strong Fire attacker; very glassy as a Shadow.",
    ),
    PokemonRaidEntry(
        "Throh",
        (15, 6, 5),
        final_form="Throh",
        role="Fighting (very low DPS)",
        base=52,
        notes="No raid relevance; belongs in PvP/collection, not raids.",
    ),
    PokemonRaidEntry(
        "Moltres",
        (11, 13, 14),
        final_form="Moltres",
        role="Fire/Flying DPS (legend)",
        base=85,
        notes="Strong Fire or Flying attacker; still relevant in many raids.",
    ),
    PokemonRaidEntry(
        "Shadow Giratina",
        (11, 9, 14),
        final_form="Shadow Giratina (Origin preferred)",
        role="Ghost/Dragon DPS (apex)",
        base=95,
        shadow=True,
        notes="Shadow Giratina debuted recently; Origin Forme is an elite Ghost raider.",
    ),
    PokemonRaidEntry(
        "Shadow Roggenrola",
        (10, 12, 5),
        final_form="Shadow Gigalith (Meteor Beam)",
        role="Rock DPS (strong)",
        base=83,
        shadow=True,
        needs_tm=True,
        notes="Meteor Beam is key; shadow gives it serious punch.",
    ),
    PokemonRaidEntry(
        "Excadrill (Dynamax)",
        (14, 14, 10),
        final_form="Excadrill",
        role="Ground DPS (top non-legend)",
        base=86,
        notes="Dynamax tag doesn't change its standard raid role; very good Ground attacker.",
    ),
]


RAID_ENTRIES = DEFAULT_RAID_ENTRIES

__all__ = [
    "DEFAULT_RAID_ENTRIES",
    "IVSpread",
    "PokemonRaidEntry",
    "RAID_ENTRIES",
    "build_entry_rows",
    "build_rows",
]
