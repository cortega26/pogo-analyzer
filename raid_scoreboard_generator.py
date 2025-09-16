"""
Raid Scoreboard Generator
-------------------------
This script builds a sortable raid value scoreboard for your listed Pokémon,
scoring each entry on a 1–100 scale based on:
- Species baseline (final raid form & meta placement)
- IV contribution (Atk-weighted for raids)
- Lucky cost efficiency
- Move requirements (Community Day / Elite TM)
- Mega availability (now/soon) for team boost utility

Outputs:
- Console preview (head of table)
- CSV at ./raid_scoreboard.csv with full data
- Excel at ./raid_scoreboard.xlsx with full data

Notes:
- This is a guide heuristic, not a simulator. Use it to set priorities quickly.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence

try:  # Pandas provides richer output; fall back to a lightweight table otherwise.
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - exercised when pandas is absent.
    pd = None  # type: ignore[assignment]


Row = Dict[str, Any]


class SimpleSeries:
    """Minimal pandas.Series stand-in used when pandas is unavailable."""

    def __init__(self, data: Iterable[Any]):
        self._data = list(data)

    def apply(self, func: Callable[[Any], Any]):
        return SimpleSeries(func(item) for item in self._data)

    def to_list(self) -> List[Any]:
        return list(self._data)

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


class SimpleTable:
    """Lightweight, pandas-like table to keep the script functional without pandas."""

    def __init__(self, rows: Sequence[Row], columns: Sequence[str] | None = None):
        self._rows = [dict(row) for row in rows]
        discovered_columns: List[str] = []
        discovered_set: set[str] = set()
        for row in self._rows:
            for key in row.keys():
                if key not in discovered_set:
                    discovered_columns.append(key)
                    discovered_set.add(key)
        if columns is None:
            final_columns: List[str] = list(discovered_columns)
        else:
            final_columns = list(columns)
            column_set = set(final_columns)
            for key in discovered_columns:
                if key not in column_set:
                    final_columns.append(key)
                    column_set.add(key)
        self._columns: List[str] = list(final_columns)
        self._column_set: set[str] = set(self._columns)
        for row in self._rows:
            for column in self._columns:
                row.setdefault(column, "")

    def sort_values(self, by: str, ascending: bool = True):
        reverse = not ascending
        sorted_rows = sorted(self._rows, key=lambda item: item.get(by), reverse=reverse)
        return SimpleTable(sorted_rows, self._columns)

    def reset_index(self, drop: bool = False):
        if drop:
            return SimpleTable(self._rows, self._columns)
        indexed_rows: List[Row] = []
        for idx, row in enumerate(self._rows):
            new_row = dict(row)
            new_row["index"] = idx
            indexed_rows.append(new_row)
        columns = ["index"] + [col for col in self._columns if col != "index"]
        return SimpleTable(indexed_rows, columns)

    def __getitem__(self, key: str) -> SimpleSeries:
        return SimpleSeries(row.get(key, "") for row in self._rows)

    def __setitem__(self, key: str, value: Iterable[Any]) -> None:
        if isinstance(value, SimpleSeries):
            values = value.to_list()
        else:
            values = list(value)
        if len(values) != len(self._rows):
            raise ValueError("Column length mismatch.")
        for row, val in zip(self._rows, values):
            row[key] = val
        if key not in self._column_set:
            self._columns.append(key)
            self._column_set.add(key)

    def to_csv(self, path: Path, index: bool = False) -> None:  # noqa: ARG002 - parity with pandas signature
        with Path(path).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self._columns)
            writer.writeheader()
            writer.writerows(self._rows)

    def to_excel(self, path: Path, index: bool = False) -> None:  # noqa: ARG002 - parity with pandas signature
        raise RuntimeError("Excel export requires pandas to be installed.")

    def head(self, n: int):
        return SimpleTable(self._rows[:n], self._columns)

    def to_string(self, index: bool = True) -> str:
        if not self._rows:
            return ""
        columns = list(self._columns)
        data = [[str(row.get(col, "")) for col in columns] for row in self._rows]
        if index:
            index_width = max(len(str(len(data) - 1)), len("index"))
            index_header = "index"
            headers = [index_header] + columns
            widths = [index_width] + [len(col) for col in columns]
            rows = [[str(i)] + row for i, row in enumerate(data)]
        else:
            headers = columns
            widths = [len(col) for col in columns]
            rows = data
        for row in rows:
            for idx, cell in enumerate(row):
                widths[idx] = max(widths[idx], len(cell))
        header_line = "  ".join(title.ljust(widths[idx]) for idx, title in enumerate(headers)).rstrip()
        line_items = [header_line]
        for row in rows:
            line_items.append("  ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row)).rstrip())
        return "\n".join(line_items)


def _as_table(rows: Sequence[Row]):
    if pd is not None:
        return pd.DataFrame(rows)
    return SimpleTable(rows)


def iv_bonus(a: int, d: int, s: int) -> float:
    """Light-touch IV bonus for raids; Attack weighted more."""
    return round((a/15)*2.0 + (d/15)*0.5 + (s/15)*0.5, 2)  # max ~3.0


def score(base: float, ivb: float = 0.0, lucky: bool = False, needs_tm: bool = False,
          mega_bonus_now: bool = False, mega_bonus_soon: bool = False) -> float:
    """Aggregate score with bounded range [1, 100]."""
    sc = base + ivb
    if lucky:
        sc += 3
    if needs_tm:
        sc -= 2
    if mega_bonus_now:
        sc += 4
    elif mega_bonus_soon:
        sc += 1
    return max(1, min(100, round(sc, 1)))


def add(rows: list, name: str, ivs: tuple, lucky: bool = False, shadow: bool = False,
        final_form: str = "", role: str = "", base: float = 70.0, needs_tm: bool = False,
        mega_now: bool = False, mega_soon: bool = False, notes: str = "") -> None:
    """Append a single Pokémon row to the rows list."""
    a, d, s = ivs
    rows.append({
        "Your Pokémon": f"{name}{' (lucky)' if lucky else ''}{' (shadow)' if shadow else ''}",
        "IV (Atk/Def/Sta)": f"{a}/{d}/{s}",
        "Final Raid Form": final_form,
        "Primary Role": role,
        "Move Needs (CD/ETM?)": "Yes" if needs_tm else "No",
        "Mega Available": "Yes" if mega_now else ("Soon" if mega_soon else "No"),
        "Raid Score (1-100)": score(base, iv_bonus(a, d, s), lucky=lucky, needs_tm=needs_tm,
                                    mega_bonus_now=mega_now, mega_bonus_soon=mega_soon),
        "Why it scores like this": notes
    })


def build_dataframe():
    """Construct the full table with all entries."""
    rows = []

    # 1) Snover -> Abomasnow/Mega Abomasnow
    add(rows, "Snover", (14, 12, 14), final_form="Abomasnow / Mega Abomasnow",
        role="Ice (mega support)", base=80, mega_now=True,
        notes="Mega Abomasnow is a strong Ice/Grass team booster; regular Abomasnow is serviceable but not top DPS.")

    # 2) Riolu (two entries) -> Lucario
    add(rows, "Riolu #1", (14, 12, 13), final_form="Lucario", role="Fighting DPS",
        base=89, needs_tm=True,
        notes="Lucario with Aura Sphere is top-tier Fighting; may require event/Elite TM for optimal moves.")
    add(rows, "Riolu #2", (13, 15, 12), final_form="Lucario", role="Fighting DPS",
        base=89, needs_tm=True,
        notes="Same as above — excellent attacker with the right moves.")

    # 3) Numel -> Camerupt / Mega Camerupt (soon)
    add(rows, "Numel", (15, 13, 11), final_form="Camerupt / Mega Camerupt", role="Fire/Ground (mega support)",
        base=76, mega_soon=True,
        notes="Regular Camerupt is weak; Mega Camerupt debut is imminent and mainly useful as a lobby booster.")

    # 4) Exeggutor (lucky) — already evolved
    add(rows, "Exeggutor", (15, 13, 13), lucky=True, final_form="Exeggutor", role="Grass/Psychic (budget)",
        base=70, notes="Outclassed by modern Grass/Psychic attackers; Lucky makes it cheap if you need filler.")

    # 5) Lopunny -> Mega Lopunny
    add(rows, "Lopunny", (15, 13, 14), final_form="Mega Lopunny", role="Fighting mega support",
        base=78, mega_now=True, notes="Personal DPS is middling, but Mega boosts Fighting/Normal teams.")

    # 6) Starly (lucky) -> Staraptor
    add(rows, "Starly", (14, 12, 15), lucky=True, final_form="Staraptor (Gust)", role="Flying DPS (budget)",
        base=77, needs_tm=True, notes="Gust is CD-only; with Gust it's a solid budget flier.")

    # 7) Flabébé set -> Florges
    add(rows, "Flabebe (lucky)", (14, 13, 15), lucky=True, final_form="Florges", role="Fairy (low DPS)",
        base=58, notes="Florges has low raid DPS; mainly collection/PvP.")
    add(rows, "Flabebe #2", (15, 11, 11), final_form="Florges",
        role="Fairy (low DPS)", base=58, notes="Same as above.")
    add(rows, "Flabebe #3", (15, 13, 15), final_form="Florges",
        role="Fairy (low DPS)", base=58, notes="Same as above.")
    add(rows, "Flabebe #4", (15, 13, 15), final_form="Florges",
        role="Fairy (low DPS)", base=58, notes="Same as above.")

    # 8) Litten -> Incineroar (Blast Burn)
    add(rows, "Litten", (15, 10, 15), final_form="Incineroar (Blast Burn)", role="Fire DPS (mid)",
        base=78, needs_tm=True, notes="CD move Blast Burn needed; still behind top Fire like Reshiram/Blaziken/Chandelure.")

    # 9) Heracross (many) -> Heracross / Mega Heracross
    for i, ivs in enumerate([(13, 11, 5), (14, 0, 10), (10, 9, 5), (12, 8, 11), (13, 8, 14)], 1):
        add(rows, f"Heracross #{i}", ivs, final_form="Mega Heracross", role="Bug/Fighting (mega & DPS)",
            base=90, mega_now=True,
            notes="Mega Heracross is one of the strongest Bug attackers and solid Fighting mega.")

    # 10) Shadow Tyrunt -> Shadow Tyrantrum
    add(rows, "Shadow Tyrunt", (14, 15, 5), shadow=True, final_form="Shadow Tyrantrum",
        role="Rock/Dragon DPS (niche)", base=80,
        notes="Fun and strong on paper, but still behind top Rock/Dragon specialists in most raids.")

    # 11) Beldum -> Metagross (Meteor Mash)
    add(rows, "Beldum", (15, 9, 4), final_form="Metagross (Meteor Mash)", role="Steel DPS (top)",
        base=90, needs_tm=True, notes="Meteor Mash is mandatory; top Steel attacker when built.")

    # 12) Electabuzz -> Electivire
    add(rows, "Electabuzz", (15, 10, 3), final_form="Electivire", role="Electric DPS (good)",
        base=82, notes="Strong budget Electric; behind Legendaries and Shadows but still very usable.")

    # 13) Gurdurr -> Conkeldurr
    add(rows, "Gurdurr", (12, 6, 14), final_form="Conkeldurr", role="Fighting DPS (top non-mega)",
        base=86, notes="Conkeldurr is a top non-mega Fighting attacker.")

    # 14) Crawdaunt (lucky)
    add(rows, "Crawdaunt", (15, 13, 15), lucky=True, final_form="Crawdaunt", role="Water/Dark (spice)",
        base=60, notes="Glass cannon, outclassed by most Water/Dark specialists.")

    # 15) Shadow Magnemite -> Shadow Magnezone
    add(rows, "Shadow Magnemite", (11, 6, 10), shadow=True, final_form="Shadow Magnezone",
        role="Electric DPS (top non-legend)", base=88,
        notes="Shadow Magnezone is among the best non-legend Electric attackers.")

    # 16) Shadow Gastly -> Shadow Gengar
    add(rows, "Shadow Gastly", (9, 11, 15), shadow=True, final_form="Shadow Gengar",
        role="Ghost DPS (apex glass cannon)", base=93, needs_tm=True,
        notes="Shadow Gengar has elite DPS; benefits from legacy Lick/Shadow Ball.")

    # 17) Treecko -> Sceptile (Frenzy Plant) / Mega Sceptile
    add(rows, "Treecko", (14, 13, 10), final_form="Sceptile (Frenzy Plant) / Mega Sceptile",
        role="Grass DPS (top w/ Mega)", base=88, needs_tm=True, mega_now=True,
        notes="Frenzy Plant Sceptile is excellent; Mega Sceptile is the best Grass mega.")

    # 18) Arcanine (already)
    add(rows, "Arcanine", (15, 12, 10), final_form="Arcanine", role="Fire DPS (mid)",
        base=72, notes="Usable but far behind top Fire options.")

    # 19) Shadow Kirlia -> Shadow Gardevoir (preferred)
    add(rows, "Shadow Kirlia", (11, 11, 11), shadow=True, final_form="Shadow Gardevoir",
        role="Fairy DPS (top non-mega)", base=88,
        notes="Shadow Gardevoir is a top non-mega Fairy attacker; consider Gardevoir over Gallade for raids.")

    # 20) Drilbur (lucky) -> Excadrill
    add(rows, "Drilbur", (14, 15, 14), lucky=True, final_form="Excadrill",
        role="Ground DPS (top non-legend)", base=86,
        notes="Excadrill has great DPS and resistances; lucky makes it cheap.")

    # 21) Grovyle -> Sceptile
    add(rows, "Grovyle", (15, 12, 13), final_form="Sceptile (Frenzy Plant) / Mega Sceptile",
        role="Grass DPS", base=88, needs_tm=True, mega_now=True,
        notes="Same as Treecko — pick your better IV to evolve.")

    # 22) Alakazam (already) / Mega Alakazam
    add(rows, "Alakazam", (14, 13, 15), final_form="Alakazam / Mega Alakazam",
        role="Psychic DPS", base=80, mega_now=True,
        notes="As a non-mega it's okay; Mega Alakazam is a strong Psychic mega booster.")

    # 23) Drowzee (lucky) -> Hypno
    add(rows, "Drowzee", (14, 15, 13), lucky=True, final_form="Hypno", role="Psychic (low DPS)",
        base=55, notes="Not raid-relevant; mostly PvP/collection.")

    # 24) Scyther -> Scizor / Mega Scizor
    add(rows, "Scyther", (12, 15, 14), final_form="Scizor / Mega Scizor", role="Bug/Steel (mega support)",
        base=82, mega_now=True, notes="Scizor is mid for raids; Mega Scizor is a handy Bug/Steel booster.")

    # 25) Hariyama (already)
    add(rows, "Hariyama", (14, 15, 12), final_form="Hariyama", role="Fighting DPS (budget)",
        base=80, notes="Solid budget Fighter; outclassed by Machamp/Conkeldurr/Lucario.")

    # 26) Blastoise (lucky) -> Mega Blastoise
    add(rows, "Blastoise", (15, 14, 14), lucky=True, final_form="Blastoise / Mega Blastoise",
        role="Water (mega support)", base=82, needs_tm=True, mega_now=True,
        notes="Hydro Cannon needed for non-mega; Mega Blastoise is a strong Water mega.")

    # 27) Machamp (lucky)
    add(rows, "Machamp", (15, 13, 14), lucky=True, final_form="Machamp",
        role="Fighting DPS (top non-shadow)", base=84,
        notes="Still a top non-legend Fighter with Counter/Dynamic Punch.")

    # 28) Shadow Drilbur -> Shadow Excadrill
    add(rows, "Shadow Drilbur", (14, 4, 15), shadow=True, final_form="Shadow Excadrill",
        role="Ground DPS (apex)", base=92,
        notes="Shadow Excadrill is among the best Ground DPS options; frailer but hits very hard.")

    # 29) Gengar (lucky)
    add(rows, "Gengar (lucky)", (15, 13, 12), lucky=True, final_form="Gengar / Mega Gengar",
        role="Ghost DPS (high)", base=82, needs_tm=True, mega_now=True,
        notes="Great non-shadow DPS; can Mega for top-tier boosts.")

    # 30) Gengar 15/15/15
    add(rows, "Gengar (hundo)", (15, 15, 15), final_form="Gengar / Mega Gengar",
        role="Ghost DPS (high)", base=85, needs_tm=True, mega_now=True,
        notes="Perfect IVs; outstanding Mega candidate.")

    # 31) Venusaur
    add(rows, "Venusaur", (15, 14, 15), final_form="Venusaur / Mega Venusaur",
        role="Grass DPS (good)", base=83, needs_tm=True, mega_now=True,
        notes="Frenzy Plant Venusaur is solid; Mega Venusaur offers bulky Grass mega support.")

    # 32) Rhyhorn -> Rhyperior (Rock Wrecker)
    add(rows, "Rhyhorn", (13, 13, 15), final_form="Rhyperior (Rock Wrecker)",
        role="Rock DPS (top TDO)", base=88, needs_tm=True,
        notes="Rock Wrecker is mandatory; elite TDO and flexible Ground coverage.")

    # 33) Gyarados (lucky)
    add(rows, "Gyarados", (14, 13, 15), lucky=True, final_form="Gyarados / Mega Gyarados",
        role="Water/Dark (mega support)", base=82, mega_now=True,
        notes="As a mega it's a great Dark/Water booster; non-mega is decent but outclassed.")

    # 34) Larvitar two IVs -> Tyranitar / Mega Tyranitar
    add(rows, "Larvitar #1", (15, 12, 13), final_form="Tyranitar (Brutal Swing) / Mega Tyranitar",
        role="Dark/Rock DPS", base=86, needs_tm=True, mega_now=True,
        notes="Brutal Swing makes Dark TTar great; Smack Down needs ETM for Rock role; Mega Tyranitar is elite.")
    add(rows, "Larvitar #2", (15, 15, 10), final_form="Tyranitar (Brutal Swing) / Mega Tyranitar",
        role="Dark/Rock DPS", base=86, needs_tm=True, mega_now=True,
        notes="Slightly better bulk; same notes as above.")

    # 35) Shadow Machoke -> Shadow Machamp
    add(rows, "Shadow Machoke", (13, 12, 7), shadow=True, final_form="Shadow Machamp",
        role="Fighting DPS (apex non-mega)", base=90,
        notes="Shadow Machamp is one of the best Fighters; very high DPS.")

    # 36) Haunter -> Gengar
    add(rows, "Haunter", (14, 14, 15), final_form="Gengar / Mega Gengar",
        role="Ghost DPS (high)", base=84, needs_tm=True, mega_now=True,
        notes="Great IVs; evolve for another strong Gengar or Mega candidate.")

    # 37) Shadow Cyndaquil -> Shadow Typhlosion (Blast Burn)
    add(rows, "Shadow Cyndaquil", (13, 0, 12), shadow=True, final_form="Shadow Typhlosion (Blast Burn)",
        role="Fire DPS (high)", base=87, needs_tm=True,
        notes="With Blast Burn it's a strong Fire attacker; very glassy as a Shadow.")

    # 38) Throh
    add(rows, "Throh", (15, 6, 5), final_form="Throh", role="Fighting (very low DPS)",
        base=52, notes="No raid relevance; belongs in PvP/collection, not raids.")

    # 39) Moltres
    add(rows, "Moltres", (11, 13, 14), final_form="Moltres", role="Fire/Flying DPS (legend)",
        base=85, notes="Strong Fire or Flying attacker; still relevant in many raids.")

    # 40) Shadow Giratina (form unspecified)
    add(rows, "Shadow Giratina", (11, 9, 14), shadow=True, final_form="Shadow Giratina (Origin preferred)",
        role="Ghost/Dragon DPS (apex)", base=95,
        notes="Shadow Giratina debuted recently; Origin Forme is an elite Ghost raider.")

    # 41) Shadow Roggenrola -> Shadow Gigalith (Meteor Beam)
    add(rows, "Shadow Roggenrola", (10, 12, 5), shadow=True,
        final_form="Shadow Gigalith (Meteor Beam)", role="Rock DPS (strong)", base=83, needs_tm=True,
        notes="Meteor Beam is key; shadow gives it serious punch.")

    # 42) Excadrill (Dynamax) — treat as built Excadrill
    add(rows, "Excadrill (Dynamax)", (14, 14, 10), final_form="Excadrill",
        role="Ground DPS (top non-legend)", base=86,
        notes="Dynamax tag doesn't change its standard raid role; very good Ground attacker.")

    return _as_table(rows)


def add_priority_tier(df):
    def tier(x: float) -> str:
        if x >= 90:
            return "S (Build ASAP)"
        if x >= 85:
            return "A (High)"
        if x >= 78:
            return "B (Good)"
        if x >= 70:
            return "C (Situational)"
        return "D (Doesn't belong on a Raids list)"
    df["Priority Tier"] = df["Raid Score (1-100)"].apply(tier)
    return df


def main() -> None:
    df = build_dataframe()
    df = df.sort_values(by="Raid Score (1-100)",
                        ascending=False).reset_index(drop=True)
    df = add_priority_tier(df)
    out_csv = Path("raid_scoreboard.csv")
    out_xlsx = Path("raid_scoreboard.xlsx")

    # Save CSV
    df.to_csv(out_csv, index=False)
    # Save Excel (requires pandas with an Excel engine installed)
    if isinstance(df, SimpleTable) or pd is None:
        print("Skipped Excel export: install pandas to enable Excel output.")
    else:
        try:
            df.to_excel(out_xlsx, index=False)
            print("Saved:", out_xlsx.resolve())
        except Exception as e:
            reason = str(e)
            lower_reason = reason.lower()
            suggestion = ""
            if "openpyxl" in lower_reason:
                suggestion = " (install openpyxl)"
            elif "xlsxwriter" in lower_reason:
                suggestion = " (install xlsxwriter)"
            print(f"Warning: failed to write Excel{suggestion}. Reason:", reason)
    print("Saved:", out_csv.resolve())
    print()
    print("Top 10 preview:")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
