# Learnsets Normaliser

`pogo-learnsets-refresh` converts a simple CSV/JSON mapping of species to their allowed PvP moves into the `learnsets.json` consumed by the PvP scoreboard.

## CSV format

Columns: `species`, `fast`, `charge`

Example:

```
species,fast,charge
Hydreigon,Snarl,Brutal Swing
Azumarill,Bubble,Play Rough
```

Multiple moves can be separated by `;` or `|`.

## Validation

The tool validates that all referenced moves exist in the normalized `moves.json` produced by `pogo-data-refresh`. Unknown names cause a descriptive error.

## Usage

```
pogo-learnsets-refresh \
  --moves-in normalized_data/normalized_moves.json \
  --map-in path/to/learnsets.csv \
  --out normalized_data/learnsets.json
```

