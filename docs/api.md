# API reference

This document highlights the public entry points exposed by PoGo Analyzer. All examples are runnable with Python 3.9+ and assume you are working from the repository root.

## Naming conventions

To keep the codebase predictable we follow these naming rules:

- **Modules and files** use `snake_case` (for example `raid_scoreboard_generator.py`).
- **Classes and dataclasses** use `PascalCase` (`PokemonRaidEntry`, `SimpleTable`).
- **Functions and methods** use descriptive `snake_case` verbs (`build_entry_rows`, `calculate_raid_score`).
- **Constants** are upper-case with underscores. Shared datasets use the `DEFAULT_` prefix (for example `DEFAULT_RAID_ENTRIES`).
- Backwards-compatible aliases such as `build_rows` or `raid_score` remain available, but new code should prefer the canonical names above.

## Module: `raid_scoreboard_generator`

| Symbol | Description |
| ------ | ----------- |
| `ScoreboardExportConfig` | Dataclass describing CSV/Excel destinations and preview behaviour. Instances are created via `build_export_config`. |
| `ExportResult` | Dataclass returned by `generate_scoreboard`/`main` summarising the produced table and file outcomes. |
| `build_dataframe(entries: Sequence[PokemonRaidEntry] = RAID_ENTRIES)` | Convert a sequence of raid entries into either a `pandas.DataFrame` (when pandas is installed) or a [`SimpleTable`](#module-pogo_analyzertablessimple_table). |
| `build_entry_rows(entries: Sequence[PokemonRaidEntry])` | Helper that transforms raid entries into dictionaries. Re-exported for convenience. |
| `add_priority_tier(df)` | Add a `"Priority Tier"` column derived from the computed raid score. Works with both DataFrame and SimpleTable instances. |
| `build_export_config(args, env=os.environ)` | Merge CLI arguments and environment variables into a `ScoreboardExportConfig`. |
| `generate_scoreboard(entries=RAID_ENTRIES, *, config)` | Build the table, apply sorting/tiers, and persist CSV/Excel files according to `config`. Returns an `ExportResult`. |
| `parse_args(argv=None)` | Convenience wrapper around `argparse` used by `main`. |
| `calculate_iv_bonus(attack_iv, defence_iv, stamina_iv)` | Re-export of `pogo_analyzer.scoring.calculate_iv_bonus`. |
| `calculate_raid_score(base_score, iv_bonus_value, **modifiers)` | Re-export of `pogo_analyzer.scoring.calculate_raid_score`. |
| `main(argv=None)` | Command-line entry point. Builds the table, writes CSV/Excel files, and prints a preview. Respects CLI flags and environment variables documented in the README. |

Legacy aliases `build_rows`, `iv_bonus`, `raid_score`, and `score` are still exported for compatibility with existing scripts.

### Building a scoreboard programmatically

```python
from raid_scoreboard_generator import (
    DEFAULT_RAID_ENTRIES,
    PokemonRaidEntry,
    add_priority_tier,
    build_dataframe,
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

## Module: `pogo_analyzer.data.raid_entries`

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
| `requires_special_move` | `bool` | Marks builds that rely on an exclusive or limited move; shown in the scoreboard’s “Move Needs” column. |
| `needs_tm` | `bool` | Subtracts 2 points when the exclusive move is still locked on the evaluated Pokémon. |
| `target_cp` | `int \| None` | Optional target combat power for a raid-ready build; powers the underpowered warning. |
| `mega_now` | `bool` | Adds +4 points when a relevant mega evolution is currently available. |
| `mega_soon` | `bool` | Adds +1 point when a mega evolution is confirmed but not yet released. |
| `notes` | `str` | Free-form explanation shown in the scoreboard. |

Invalid IV spreads, empty names, and baseline scores outside the inclusive
range `[1, 100]` now raise exceptions during construction so issues surface
early when assembling datasets.

Convenience methods:

- `formatted_name()` – Append `(lucky)` and `(shadow)` labels when relevant.
- `iv_text()` – Render the IV tuple as `"15/14/13"`.
- `mega_text()` – Display `"Yes"`, `"Soon"`, or `"No"` for mega availability.
- `move_text()` – Return `"Yes"` when `requires_special_move` is set.
- `target_cp` – Optional attribute you can set directly when instantiating the dataclass.
- `to_row()` – Produce a `dict[str, Any]` matching the scoreboard column schema.
- `as_row()` – Backwards-compatible alias for `to_row()`.

#### Building rows manually

```python
from pogo_analyzer.data import DEFAULT_RAID_ENTRIES, PokemonRaidEntry, build_entry_rows
from pogo_analyzer.scoring import calculate_iv_bonus

entry = PokemonRaidEntry(
    "Kartana",
    (15, 15, 15),
    final_form="Kartana",
    role="Grass DPS",
    base=94,
    notes="One of the strongest Grass attackers even without mega support.",
)

rows = build_entry_rows([entry])
score = rows[0]["Raid Score (1-100)"]
print("Computed score:", score)
print("IV bonus portion:", calculate_iv_bonus(*entry.ivs))
print("Default dataset entries:", len(DEFAULT_RAID_ENTRIES))
```

`RAID_ENTRIES` and `build_rows` remain available as aliases for existing imports.

## Module: `pogo_analyzer.scoring`

- `calculate_iv_bonus(attack_iv: int, defence_iv: int, stamina_iv: int) -> float` – Calculate the additive IV modifier with Attack weighted ×2 and Defence/Stamina weighted ×0.5. The return value is rounded to two decimal places (maximum of roughly 3.0).
- `calculate_raid_score(base_score: float, iv_bonus_value: float = 0.0, *, lucky: bool = False, needs_tm: bool = False, mega_bonus_now: bool = False, mega_bonus_soon: bool = False) -> float` – Combine the baseline score, IV bonus, and optional modifiers. Results are clamped to the inclusive range [1, 100].
- `iv_bonus(...)` / `raid_score(...)` – Compatibility wrappers for the legacy function names.

### Reproducing the score used in the dataset

```python
from pogo_analyzer.data import DEFAULT_RAID_ENTRIES
from pogo_analyzer.scoring import calculate_iv_bonus, calculate_raid_score

first = DEFAULT_RAID_ENTRIES[0]
attack, defence, stamina = first.ivs
computed = calculate_raid_score(
    first.base,
    calculate_iv_bonus(attack, defence, stamina),
    lucky=first.lucky,
    needs_tm=first.needs_tm,
    mega_bonus_now=first.mega_now,
    mega_bonus_soon=first.mega_soon,
)
assert computed == first.to_row()["Raid Score (1-100)"]
```

## Module: `pogo_analyzer.tables.simple_table`

A dependency-free subset of the `pandas.DataFrame` API. Returned when pandas is unavailable.

### `SimpleSeries`

- `SimpleSeries(data)` – Create a wrapper around an iterable.
- `apply(func)` – Return a new `SimpleSeries` with `func` applied to each element.
- `to_list()` – Materialise the series as a list.
- Standard Python iteration (`for value in series`) is supported.

### `SimpleTable`

- `SimpleTable(rows, columns=None)` – Construct a table from a list of dictionaries. Missing values default to empty strings. When `columns` is omitted, headers are discovered from the supplied rows in order of first appearance.
- `sort_values(by, ascending=True)` – Return a new table sorted by the provided column. Raises `KeyError` when the column is missing.
- `reset_index(drop=False)` – Mirror `pandas.DataFrame.reset_index`. When `drop=False`, an `index` column is added.
- `__getitem__(column)` – Provide a `SimpleSeries` for compatibility with pandas' column access. Raises `KeyError` when the column is missing, matching pandas semantics.
- `__setitem__(column, values)` – Add or overwrite a column. Accepts iterables or other `SimpleSeries` instances.
- `to_csv(path, index=False)` – Persist the table as UTF-8 CSV.
- `to_excel(path, index=False)` – Raise `RuntimeError`; included for parity with pandas.
- `head(n)` – Return the first `n` rows.
- `to_string(index=True)` – Render a padded table string for console previews.

```python
from pogo_analyzer.tables import SimpleTable

rows = [
    {"Name": "Shadow Mamoswine", "Raid Score (1-100)": 91.2},
    {"Name": "Mega Gengar", "Raid Score (1-100)": 94.5},
]

preview = SimpleTable(rows).to_string(index=False)
print(preview)
```
