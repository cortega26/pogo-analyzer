# Data Refresh (Offline Normaliser)

`pogo-data-refresh` is a small CLI that validates and normalises pre-scraped datasets into JSON files the tools can consume. It does not scrape the web; you supply input files exported from trusted sources.

## Usage

```
pogo-data-refresh \
  --species-in path/to/species.json \
  --moves-in path/to/moves.json \
  --out-dir normalized_data \
  --prefix normalized \
  --source-tag gamepress-2025-09
```

Writes two files by default:

- `normalized_data/normalized_species.json`
- `normalized_data/normalized_moves.json`

Both include a `metadata` block with a `generated_at` timestamp (UTC) and simple counts.

## Input schema

The CLI currently expects JSON inputs with these shapes:

- Species:
  ```json
  {
    "species": [
      {"name": "Hydreigon", "base_attack": 256, "base_defense": 188, "base_stamina": 211}
    ]
  }
  ```

- Moves:
  ```json
  {
    "fast": [
      {"name": "Snarl", "damage": 5, "energy_gain": 13, "turns": 4, "availability": "standard"}
    ],
    "charge": [
      {"name": "Brutal Swing", "damage": 65, "energy_cost": 40, "reliability": null, "has_buff": false, "availability": "standard"}
    ]
  }
  ```

Validation rules are strict: names must be non-empty; base stats must be positive integers; fast `energy_gain>0` and `turns>0`; charge `energy_cost>0`. Availability is an optional string tag copied through.

## Guardrails

- No network access or scraping is performed; this is strictly a local normaliser.
- Use the tool to prepare weekly snapshots from sources like GO Hub / GamePress / PvPoke while respecting their terms.
- Include a `--source-tag` so you can track provenance in downstream artifacts.

