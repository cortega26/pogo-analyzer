# PoGo Analyzer

[![CI](https://github.com/pogo-analyzer/pogo-analyzer/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/pogo-analyzer/pogo-analyzer/actions/workflows/ci.yml)
[![CI – Linux/macOS/Windows](https://img.shields.io/github/actions/workflow/status/pogo-analyzer/pogo-analyzer/ci.yml?branch=main&label=Linux%2FmacOS%2FWindows)](https://github.com/pogo-analyzer/pogo-analyzer/actions/workflows/ci.yml)
[![CI – Python 3.9–3.12](https://img.shields.io/github/actions/workflow/status/pogo-analyzer/pogo-analyzer/ci.yml?branch=main&label=Python%203.9%E2%80%933.12)](https://github.com/pogo-analyzer/pogo-analyzer/actions/workflows/ci.yml)

PoGo Analyzer is a lightweight toolkit for evaluating Pokémon GO raid investments. It ships with a ready-to-run scoreboard generator that grades your Pokémon on a 1–100 scale and exports the results as CSV (and Excel when pandas is available). All functionality is implemented in pure Python so you can run the scripts anywhere, with optional pandas support for richer tabular output.

## Features

- 📊 **Raid value scoreboard** – score your roster by combining baseline species strength, IV quality, lucky cost savings, move requirements, and mega availability.
- 🧮 **Reusable scoring helpers** – import the library to compute raid scores or transform entries inside your own automation scripts.
- 🗃️ **Pandas-free tables** – fall back to a minimal in-repo table implementation when pandas is not installed.
- 🧪 **Tested behavior** – regression tests cover key scoring, formatting, and export scenarios.

## Requirements

- Python 3.9 or newer
- Optional: [pandas](https://pandas.pydata.org/) with an Excel writer engine for `.xlsx` export (`openpyxl` or `xlsxwriter`)

## Installation

Clone the repository and install the package into your virtual environment:

```bash
git clone https://github.com/<your-user>/pogo-analyzer.git
cd pogo-analyzer
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install .
# Enable Excel exports with pandas and openpyxl
pip install .[pandas]
```

If you only need the CSV output, you can skip installing the optional ``[pandas]`` extra.

### Excel export extras

Excel files are produced through pandas and an accompanying writer engine:

- ``pogo-analyzer[pandas]`` installs pandas alongside ``openpyxl`` (the default writer)
- ``xlsxwriter`` can be installed separately if you prefer that engine over ``openpyxl``

The [`requirements.txt`](requirements.txt) file lists these optional dependencies when you need to vendor them explicitly.

## Quick start

1. Add or adjust your Pokémon entries in [`pogo_analyzer/data/raid_entries.py`](pogo_analyzer/data/raid_entries.py).
2. Run the scoreboard generator:

   ```bash
   pogo-raid-scoreboard
   ```

   Use ``--output-dir``/``--csv-name``/``--excel-name`` to customise export
   locations, or ``--no-excel`` when you only want the CSV output. ``--preview-limit``
   controls how many rows are printed to the console preview.

3. Inspect the generated files in the project root (or your configured directory):
   - `raid_scoreboard.csv` – always produced
   - `raid_scoreboard.xlsx` – requires pandas with an Excel engine

The script also prints a preview of the top ten entries to standard output.

### Configuration

The generator follows 12-factor-style configuration. Environment variables are
merged with CLI options so you can adjust defaults without editing code:

- ``RAID_SCOREBOARD_OUTPUT_DIR`` – base directory for exports.
- ``RAID_SCOREBOARD_CSV`` / ``RAID_SCOREBOARD_EXCEL`` – override file names.
- ``RAID_SCOREBOARD_DISABLE_EXCEL`` – set to ``true``/``1`` to skip Excel.
- ``RAID_SCOREBOARD_PREVIEW_LIMIT`` – change the default preview row count.

### Library usage

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
        needs_tm=True,
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

### Exporting without pandas

When pandas is unavailable the scripts transparently fall back to `SimpleTable`. You still receive a CSV file and console preview. Attempting to export Excel without pandas prints a friendly warning along with suggestions for installing an engine such as `openpyxl`.

## Updating the dataset

Each raid entry is defined via the [`PokemonRaidEntry`](docs/api.md#pokemonraidentry) dataclass. Supply the Pokémon's name, IV spread, baseline rating, and any flags that affect the computed score. The [`docs/api.md`](docs/api.md) reference includes a full parameter breakdown and scoring formula.

## Testing

Run the unit tests whenever you change scoring logic or table utilities:

```bash
pytest
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for pull request, coding-style, and documentation guidelines.

## License

This project is licensed under the [MIT License](LICENSE).
