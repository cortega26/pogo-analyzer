# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Placeholder for upcoming changes.

## [0.2.0] - 2025-09-18

### Added
- Enhanced PvE/PvP scoring formulas with feature-flagged defaults (`--enhanced-defaults`) in single-Pokémon quick checks.
- New CLIs:
  - `pogo-data-refresh` — offline normaliser for species and moves JSON.
  - `pogo-learnsets-refresh` — normaliser for species→moves learnsets (CSV/JSON → JSON).
  - `pogo-pvp-scoreboard` — generates `pvp_scoreboard.csv` from normalized datasets.
- Advanced CLI toggles for PvE (dodge, breakpoints, coverage, availability) and PvP (CMP, coverage, bait model, weights).
- Optional IV optimisation mode for PvP scoreboard (`--iv-mode max-sp`, `--iv-floor`).
- Documentation: `docs/pvp.md`, `docs/data_refresh.md`, `docs/learnsets.md`, and expanded `docs/cli.md`.
- Comprehensive tests across formulas, CLIs, modifiers, normalisers, and scoreboard smoke/golden checks.

### Fixed
- Resolved a syntax error in `pogo_analyzer/pvp.py` and aligned `compute_pvp_score` signature with CLI/tests (`league_configs`).

### Security/Quality
- Stricter validation and clean error reporting in CLI parsers and normalisers to avoid silent failures.

## [0.1.0] - 2024-05-09

### Added
- Initial release of the raid scoring utilities and scoreboard generator.
