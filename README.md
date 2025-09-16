# PoGo Analyzer

PoGo Analyzer is a lightweight toolkit for evaluating Pokémon GO raid investments. It ships with a ready-to-run scoreboard generator that grades your Pokémon on a 1–100 scale and exports the results as CSV (and Excel when pandas is available). All functionality is implemented in pure Python so you can run the scripts anywhere, with optional pandas support for richer tabular output.

## Features

- 📊 **Raid value scoreboard** – score your roster by combining baseline species strength, IV quality, lucky cost savings, move requirements, and mega availability.
- 🧮 **Reusable scoring helpers** – import the library to compute raid scores or transform entries inside your own automation scripts.
- 🗃️ **Pandas-free tables** – fall back to a minimal in-repo table implementation when pandas is not installed.
- 🧪 **Tested behavior** – regression tests cover key scoring, formatting, and export scenarios.

## Requirements

- Python 3.9 or newer
- Optional: [pandas](https://pandas.pydata.org/) plus an Excel writer (``openpyxl`` or ``xlsxwriter``) for `.xlsx` export

## Installation

Clone the repository and install the optional dependencies when you want Excel output:

```bash
git clone https://github.com/<your-user>/pogo-analyzer.git
cd pogo-analyzer
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt  # if you create one, otherwise install pandas manually
```

If you only need the CSV output, you can skip installing pandas entirely.

## Quick start

1. Add or adjust your Pokémon entries in [`pogo_analyzer/data/raid_entries.py`](pogo_analyzer/data/raid_entries.py).
2. Run the scoreboard generator:

   ```bash
   python raid_scoreboard_generator.py
   ```

3. Inspect the generated files in the project root:
   - `raid_scoreboard.csv` – always produced
   - `raid_scoreboard.xlsx` – requires pandas with an Excel engine

The script also prints a preview of the top ten entries to standard output.

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
python -m unittest
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for pull request, coding-style, and documentation guidelines.

## License

This project inherits the license of the upstream repository. Add a LICENSE file if you plan to distribute your own fork.
