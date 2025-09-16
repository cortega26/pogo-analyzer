# API reference

This document highlights the public entry points exposed by PoGo Analyzer. All examples are runnable with Python 3.9+ and assume you are working from the repository root.

## Module: `raid_scoreboard_generator`

| Symbol | Description |
| ------ | ----------- |
| `build_dataframe(entries: Sequence[PokemonRaidEntry] = RAID_ENTRIES)` | Convert a sequence of raid entries into either a `pandas.DataFrame` (when pandas is installed) or a [`SimpleTable`](#module-pogo_analyzersimple_table). |
| `add_priority_tier(df)` | Add a `"Priority Tier"` column derived from the computed raid score. Works with both DataFrame and SimpleTable instances. |
| `main()` | Command-line entry point. Builds the table, writes CSV/Excel files, and prints a preview. |

### Building a scoreboard programmatically

```python
from raid_scoreboard_generator import (
    PokemonRaidEntry,
    build_dataframe,
    add_priority_tier,
)

def preview(entries):
    df = build_dataframe(entries)
    df = df.sort_values(by="Raid Score (1-100)", ascending=False)
    df = add_priority_tier(df)
    print(df.head(5).to_string(index=False))

preview([
    PokemonRaidEntry(
        "Rayquaza",
        (15, 14, 15),
        final_form="Mega Rayquaza",
        role="Dragon/Flying DPS",
        base=95,
        mega_now=True,
        notes="Near-maximum raid score thanks to overwhelming DPS and mega utility.",
    )
])
```

## Module: `pogo_analyzer.raid_entries`

### `PokemonRaidEntry`

Immutable dataclass representing one row on the raid scoreboard.

| Field | Type | Purpose |
| ----- | ---- | ------- |
| `name` | `str` | Nickname or identifier shown in the table. |
| `ivs` | `tuple[int, int, int]` | Attack, Defence, Stamina IVs. Attack carries the greatest weight in the final score. |
| `final_form` | `str` | Evolutions or mega forms you intend to build. |
| `role` | `str` | Short description of the Pokémon's raid role (e.g., `"Fighting DPS"`). |
| `base` | `float` | Baseline score for the species before modifiers. Typical values range from 55–95. |
| `lucky` | `bool` | Adds +3 to the raid score to reflect reduced dust costs. |
| `shadow` | `bool` | Indicates the Pokémon is a Shadow variant. Used for labelling only—the damage boost is baked into the baseline score you provide. |
| `needs_tm` | `bool` | Subtracts 2 points when a Community Day or Elite TM move is required. |
| `mega_now` | `bool` | Adds +4 points when a relevant mega evolution is currently available. |
| `mega_soon` | `bool` | Adds +1 point when a mega evolution is confirmed but not yet released. |
| `notes` | `str` | Free-form explanation shown in the scoreboard. |

Convenience methods:

- `formatted_name()` – Append `(lucky)` and `(shadow)` labels when relevant.
- `iv_text()` – Render the IV tuple as `"15/14/13"`.
- `mega_text()` – Display `"Yes"`, `"Soon"`, or `"No"` for mega availability.
- `move_text()` – Return `"Yes"` when special moves are needed.
- `as_row()` – Produce a `dict[str, Any]` matching the scoreboard column schema.

#### Building rows manually

```python
from pogo_analyzer.raid_entries import PokemonRaidEntry, build_rows
from pogo_analyzer.scoring import iv_bonus

entry = PokemonRaidEntry(
    "Kartana",
    (15, 15, 15),
    final_form="Kartana",
    role="Grass DPS",
    base=94,
    notes="One of the strongest Grass attackers even without mega support.",
)

rows = build_rows([entry])
score = rows[0]["Raid Score (1-100)"]
print("Computed score:", score)
print("IV bonus portion:", iv_bonus(*entry.ivs))
```

## Module: `pogo_analyzer.scoring`

- `iv_bonus(a: int, d: int, s: int) -> float` – Calculate the additive IV modifier with Attack weighted ×2 and Defence/Stamina weighted ×0.5. The return value is rounded to two decimal places (maximum of roughly 3.0).
- `raid_score(base: float, ivb: float = 0.0, *, lucky: bool = False, needs_tm: bool = False, mega_bonus_now: bool = False, mega_bonus_soon: bool = False) -> float` – Combine the baseline score, IV bonus, and optional modifiers. Results are clamped to the inclusive range [1, 100].

### Reproducing the score used in the dataset

```python
from pogo_analyzer.raid_entries import RAID_ENTRIES
from pogo_analyzer.scoring import iv_bonus, raid_score

first = RAID_ENTRIES[0]
attack, defence, stamina = first.ivs
computed = raid_score(
    first.base,
    iv_bonus(attack, defence, stamina),
    lucky=first.lucky,
    needs_tm=first.needs_tm,
    mega_bonus_now=first.mega_now,
    mega_bonus_soon=first.mega_soon,
)
assert computed == first.as_row()["Raid Score (1-100)"]
```

## Module: `pogo_analyzer.simple_table`

A dependency-free subset of the `pandas.DataFrame` API. Returned when pandas is unavailable.

### `SimpleSeries`

- `SimpleSeries(data)` – Create a wrapper around an iterable.
- `apply(func)` – Return a new `SimpleSeries` with `func` applied to each element.
- `to_list()` – Materialise the series as a list.
- Standard Python iteration (`for value in series`) is supported.

### `SimpleTable`

- `SimpleTable(rows, columns=None)` – Construct a table from a list of dictionaries. Missing values default to empty strings. When `columns` is omitted, headers are discovered from the supplied rows in order of first appearance.
- `sort_values(by, ascending=True)` – Return a new table sorted by the provided column.
- `reset_index(drop=False)` – Mirror `pandas.DataFrame.reset_index`. When `drop=False`, an `index` column is added.
- `__getitem__(column)` – Provide a `SimpleSeries` for compatibility with pandas' column access.
- `__setitem__(column, values)` – Add or overwrite a column. Accepts iterables or other `SimpleSeries` instances.
- `to_csv(path, index=False)` – Persist the table as UTF-8 CSV.
- `to_excel(path, index=False)` – Raise `RuntimeError`; included for parity with pandas.
- `head(n)` – Return the first `n` rows.
- `to_string(index=True)` – Render a padded table string for console previews.

```python
from pogo_analyzer.simple_table import SimpleTable

rows = [
    {"Name": "Shadow Mamoswine", "Raid Score (1-100)": 91.2},
    {"Name": "Mega Gengar", "Raid Score (1-100)": 94.5},
]

preview = SimpleTable(rows).to_string(index=False)
print(preview)
```

