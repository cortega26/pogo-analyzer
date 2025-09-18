# PoGo Analyzer

[![CI](https://github.com/cortega26/pogo-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/cortega26/pogo-analyzer/actions/workflows/ci.yml)
[![Test Matrix](https://img.shields.io/github/actions/workflow/status/cortega26/pogo-analyzer/ci.yml?label=CI%20matrix&logo=github)](https://github.com/cortega26/pogo-analyzer/actions/workflows/ci.yml)
[![Python Versions](https://img.shields.io/badge/Python-3.9%E2%80%933.13-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

PoGo Analyzer is a lightweight toolkit for evaluating Pokémon GO raid investments. It ships with a ready-to-run scoreboard generator that grades your Pokémon on a 1–100 scale and exports the results as CSV (and Excel when pandas is available). All functionality is implemented in pure Python so you can run the scripts anywhere, with optional pandas support for richer tabular output. The CLI also offers a single-Pokémon quick check that infers the level from Combat Power, highlights missing moves, and can surface PvE/PvP value metrics without creating export files—see the [CLI quick-check guide](docs/cli.md) for end-to-end examples.

## Table of contents

- [PoGo Analyzer](#pogo-analyzer)
  - [Table of contents](#table-of-contents)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Installation](#installation)
    - [Excel export extras](#excel-export-extras)
  - [CLI usage](#cli-usage)
    - [Basic scoreboard generation](#basic-scoreboard-generation)
    - [Custom export locations](#custom-export-locations)
    - [Environment configuration](#environment-configuration)
    - [Single Pokémon quick check](#single-pokémon-quick-check)
  - [Library examples](#library-examples)
  - [Dataset maintenance](#dataset-maintenance)
  - [Testing](#testing)
  - [Contributing](#contributing)
  - [License](#license)

## Features

- **Raid value scoreboard** – score your roster by combining baseline species strength, IV quality, lucky cost savings, move requirements, and mega availability.
- **CP→Level inference** – feed base stats, IVs, and Combat Power into the quick check to recover the underlying level and CPM alongside effective raid stats.
- **Reusable scoring helpers** – import the library to compute raid scores or transform entries inside your own automation scripts.
- **Pandas-free tables** – fall back to a minimal in-repo table implementation when pandas is not installed.
- **Repeatable workflows** – the CLI works with configuration flags and environment variables so it is easy to wire into cron jobs or CI pipelines.
- **Tested behavior** – regression tests cover key scoring, formatting, and export scenarios.

## Requirements

- Python 3.9 or newer
- Optional: [pandas](https://pandas.pydata.org/) with an Excel writer engine for `.xlsx` export (`openpyxl` or `xlsxwriter`)

## Installation

Clone the repository and install the package into your virtual environment:

```bash
git clone https://github.com/cortega26/pogo-analyzer.git
cd pogo-analyzer
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install .
# Enable Excel exports with pandas and openpyxl
pip install .[pandas]
```

If you only need the CSV output, you can skip installing the optional `[pandas]` extra.

### Excel export extras

Excel files are produced through pandas and an accompanying writer engine:

- `pogo-analyzer[pandas]` installs pandas alongside `openpyxl` (the default writer)
- `xlsxwriter` can be installed separately if you prefer that engine over `openpyxl`

The [`requirements.txt`](requirements.txt) file lists these optional dependencies when you need to vendor them explicitly.

## CLI usage

`pogo-raid-scoreboard` is installed as a console script. Run `pogo-raid-scoreboard --help` to see all options:

```bash
$ pogo-raid-scoreboard --help
usage: pogo-raid-scoreboard [-h] [--output-dir OUTPUT_DIR] [--csv-name CSV_NAME]
                            [--excel-name EXCEL_NAME] [--no-excel]
                            [--preview-limit PREVIEW_LIMIT]

Generate the raid investment scoreboard.
```

### Basic scoreboard generation

```bash
pogo-raid-scoreboard
```

Produces the default `raid_scoreboard.csv` (and `raid_scoreboard.xlsx` when pandas is available) in the current directory and prints the top entries to stdout.

### Custom export locations

Specify output destinations on the command line when you want to route results elsewhere:

```bash
pogo-raid-scoreboard \
  --output-dir ~/Documents/PoGo/exports \
  --csv-name january.csv \
  --excel-name january.xlsx \
  --preview-limit 5
```

### Environment configuration

The generator follows 12-factor-style configuration. Environment variables are merged with CLI options so you can adjust defaults without editing code:

- `RAID_SCOREBOARD_OUTPUT_DIR` – base directory for exports.
- `RAID_SCOREBOARD_CSV` / `RAID_SCOREBOARD_EXCEL` – override file names.
- `RAID_SCOREBOARD_DISABLE_EXCEL` – set to `true`/`1` to skip Excel creation even when pandas is installed.
- `RAID_SCOREBOARD_PREVIEW_LIMIT` – change the default preview row count.

Example using environment variables:

```bash
export RAID_SCOREBOARD_OUTPUT_DIR=~/Documents/PoGo/weekly
export RAID_SCOREBOARD_DISABLE_EXCEL=1
pogo-raid-scoreboard
```

### Single Pokémon quick check

When you want a recommendation for one Pokémon, pass its details directly:

```bash
pogo-raid-scoreboard \
  --pokemon-name Hydreigon \
  --combat-power 3200 \
  --ivs 15 14 15 \
  --shadow \
  --needs-tm \
  --notes "Needs Brutal Swing from CD."
```

The CLI prints an on-the-spot summary including the computed raid score and priority tier without generating files.
If you already have the exclusive move unlocked, add `--has-special-move` to suppress the reminder.
Use `--target-cp` to tell the CLI what raid-ready CP you're aiming for; it only flags builds as underpowered when a target is provided.

Refer to the [CLI quick-check guide](docs/cli.md) for an expanded walkthrough that covers the available flags, expected output sections, and combined PvE/PvP scoring scenarios.

### Level inference and PvE/PvP value scoring

Provide species base stats together with your observed Combat Power to infer the underlying level and Combat Power Multiplier (CPM) for a build. Adding move descriptors unlocks PvE rotation evaluation and PvP value scoring, printing the effective stats and score components alongside the raid score summary:

```bash
pogo-raid-scoreboard \
  --pokemon-name Hydreigon \
  --species Hydreigon \
  --base-stats 256 188 216 \
  --cp 3200 \
  --ivs 15 15 15 \
  --fast 'Snarl,12,13,1.0,turns=4,stab=true' \
  --charge 'Brutal Swing,65,40,1.9,stab=true' \
  --target-defense 180 \
  --incoming-dps 35 \
  --alpha 0.6 \
  --league-cap 1500 \
  --beta 0.52
```

Move descriptors follow the format `name,power,energy_gain,duration` for fast moves and `name,power,energy_cost,duration` for charge moves. Append `stab=true`, `weather=true`, `type=1.6`, or `turns=4`/`reliability=0.8` as `key=value` pairs to model bonuses and PvP timing; pass `--weather` to apply a weather boost to all moves unless overridden per move. Use `--incoming-dps` and `--target-defense` to configure the PvE durability assumptions, and `--league-cap`/`--beta`/`--sp-ref`/`--mp-ref`/`--bait-prob` to override PvP scoring defaults. The CLI reuses `--combat-power` via the shorter `--cp` alias, recognises `--bb` as shorthand for `--best-buddy`, and accepts `--observed-hp` to disambiguate ambiguous CP values during level inference.

## Library examples

Import the package if you want to automate scoring in another script or notebook:

```python
from pogo_analyzer import (
    PokemonRaidEntry,
    build_entry_rows,
    calculate_iv_bonus,
    calculate_raid_score,
    SimpleTable,
)

entries = [
    PokemonRaidEntry(
        "Hydreigon",
        (15, 14, 15),
        final_form="Hydreigon (Brutal Swing)",
        role="Dark DPS",
        base=88,
        requires_special_move=True,
        target_cp=3700,
        notes="Top-tier Dark attacker with its Community Day move.",
    )
]

rows = build_entry_rows(entries)
# Use pandas when available; SimpleTable otherwise.
table = SimpleTable(rows)
table = table.sort_values(by="Raid Score (1-100)", ascending=False)
print(table.to_string(index=False))
print(
    "Score:",
    calculate_raid_score(entries[0].base, calculate_iv_bonus(*entries[0].ivs)),
)
```

## Dataset maintenance

Each raid entry is defined via the [`PokemonRaidEntry`](docs/api.md#pokemonraidentry) dataclass inside [`pogo_analyzer/data/raid_entries.py`](pogo_analyzer/data/raid_entries.py). Supply the Pokémon's name, IV spread, baseline rating, and any flags that affect the computed score. The [`docs/api.md`](docs/api.md) reference includes a full parameter breakdown and scoring formula.

Base species stats are resolved automatically from [`pogo_analyzer/data/base_stats.json`](pogo_analyzer/data/base_stats.json), which mirrors PvPoke's public **gamemaster** dataset. Override the lookup by passing `--base-stats` if you need to test custom stat spreads or emerging forms that have not yet landed in the dataset. Supply the Pokémon's name, IV spread, baseline rating, and any flags that affect the computed score. The [`docs/api.md`](docs/api.md) reference includes a full parameter breakdown and scoring formula.

## Testing

Run the unit tests whenever you change scoring logic or table utilities:

```bash
pytest
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for pull request, coding-style, and documentation guidelines.

## License

This project is licensed under the [MIT License](LICENSE).
