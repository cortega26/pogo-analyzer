# PvP Scoreboard

`pogo-pvp-scoreboard` generates a CSV ranking species by PvP score for a given league, using normalized inputs prepared by `pogo-data-refresh` and a per-species learnset mapping.

## Inputs

- `--species`: JSON with `{"species": [{"name": ..., "base_attack": ..., "base_defense": ..., "base_stamina": ...}, ...]}`
- `--moves`: JSON with PvP `fast` and `charge` lists (see `docs/data_refresh.md` for schema)
- `--learnsets`: JSON map: `{ "Species Name": { "fast": ["Fast 1", ...], "charge": ["Charge 1", ...] }, ... }`

## Usage

```
pogo-pvp-scoreboard \
  --species normalized_data/normalized_species.json \
  --moves normalized_data/normalized_moves.json \
  --learnsets path/to/learnsets.json \
  --league-cap 1500 \
  --output-dir pvp_exports
```

Writes `pvp_exports/pvp_scoreboard.csv`. Columns include species, level under cap, effective stats, Stat Product (SP), Move Pressure (MP), normalized values, total score, and the best fast/charge move combination chosen.

## Notes

- The tool assumes a uniform IV spread across species (default: 15/15/15). Override with `--ivs ATK DEF STA` when you want a different assumption.
- Set `--enhanced-defaults` to use the calibrated kappa/lambda/shield weights and a sigmoid bait model from the enhanced formulas.
- You can override `--sp-ref`/`--mp-ref`/`--beta`/`--shield-weights`/`--bait-prob`/`--bait-model` as needed.

