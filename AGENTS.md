# AGENTS.md — Operating Guide for AI Assistants

> **Repository:** `cortega26/pogo-analyzer`  
> **Purpose of this guide:** Equip an AI agent with the context, constraints, checklists, and commands it needs to contribute safely and effectively to this project.

---

## 1) Mission & Scope

**PoGo Analyzer** is a lightweight toolkit for evaluating **Pokémon GO raid investments**. It ships a CLI that generates a raid **scoreboard** (CSV and optionally Excel) and provides a small Python library for reuse. The focus today is **PvE (raids/gyms)** with portable, pure‑Python utilities and optional pandas support. citeturn0view0

This guide also includes **forward‑looking hooks** for PvP scoring so an agent can add that capability behind a feature flag without disrupting current users.

---

## 2) Quick Repo Map (what matters to the agent)

- `.github/workflows/` — CI pipelines (tests, packaging).  
- `benchmarks/` — micro/bench scripts for performance checks.  
- `docs/` — project docs (API, usage).  
- `pogo_analyzer/` — the library (dataclasses, scoring helpers, CLI plumbing).  
- `tests/` — unit tests (expected behavior).  
- Top‑level scripts: `raid_scoreboard_generator.py` (entrypoint used by the CLI), `microbench_simple_table.py`.  
- Project metadata: `pyproject.toml`, `requirements.txt`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`. citeturn0view0

> **Note:** The README describes the CLI command `pogo-raid-scoreboard`, core features (1–100 raid score), optional Excel export, environment variable overrides, and a small Python API example. Use it as ground truth for current behavior. citeturn0view0

---

## 3) What the project does today (baseline behavior)

- **CLI:** `pogo-raid-scoreboard [--output-dir ... --csv-name ... --excel-name ... --no-excel --preview-limit N]` produces a ranked raid scoreboard (CSV and optionally Excel) and prints a preview to stdout. It also supports **single‑Pokémon quick checks** with flags like `--pokemon-name`, `--combat-power`, `--ivs`, `--shadow`, `--needs-tm`, `--has-special-move`, and `--target-cp`. citeturn0view0
- **Library API:** Minimal helpers such as `PokemonRaidEntry`, `build_entry_rows`, `calculate_iv_bonus`, `calculate_raid_score`, and `SimpleTable` for embedding results in other scripts. citeturn0view0
- **Environment configuration:** Follows 12‑factor style; the CLI can be configured via environment variables (`RAID_SCOREBOARD_*`). citeturn0view0
- **Requirements:** Python 3.9+; optional pandas + an xlsx writer (openpyxl or xlsxwriter) for Excel output. citeturn0view0

---

## 4) High‑level agent responsibilities

1. **Preserve current PvE behavior** (raid scoring) and its outputs/contracts.  
2. **Add features safely** behind flags (e.g., PvP scoring pipeline) without breaking the CLI defaults.  
3. **Keep docs and tests in lock‑step** with any public behavior change.  
4. **Automate data refresh** when appropriate (see §10) while respecting scraping guardrails.  
5. **Maintain performance** (don’t regress basic runs; see `benchmarks/`).

---

## 5) Don’t break these contracts (guardrails)

- **CLI I/O shape is stable:** Default output files `raid_scoreboard.csv` (and `.xlsx` when enabled). Keep current column names/ordering unless a major‑version change is planned and documented. citeturn0view0
- **Backwards‑compatible flags:** Introducing new CLI flags is fine; changing/removing existing flags requires a deprecation cycle and README updates. citeturn0view0
- **Pure‑Python fallback:** Excel export must remain optional. If pandas/openpyxl aren’t installed, CSV output must still work. citeturn0view0
- **Tests must pass:** Add/update tests for new functionality and fix any failing tests before merging. (Run `pytest` locally.) citeturn0view0
- **No secrets in repo:** Never commit API keys, cookies, or scrape credentials. Use environment variables for any optional integration.
- **Deterministic results:** For the same inputs, outputs should be reproducible unless a data source changed. Stamp outputs with data version when feasible.

---

## 6) How to run things (development workflow)

```bash
# Clone and create a venv
git clone https://github.com/cortega26/pogo-analyzer.git
cd pogo-analyzer
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install (CSV only)
pip install -U pip
pip install .

# Install with Excel export support
pip install .[pandas]

# CLI help
pogo-raid-scoreboard --help

# Default run (CSV [+ Excel] in cwd)
pogo-raid-scoreboard

# Tests
pytest
```

(Commands mirror the README to keep the agent aligned with real user flows.) citeturn0view0

---

## 7) Where to plug in new work (file‑level pointers)

- **CLI** → `raid_scoreboard_generator.py` & console entrypoint wiring in `pyproject.toml`.  
- **Core data models & helpers** → `pogo_analyzer/` (look for a `data/` submodule containing `PokemonRaidEntry` and scoring calculations).  
- **Docs** → `docs/` (add user‑facing explanations, changelogs, and API references).  
- **Tests** → `tests/` (mirror CLI/library behaviors with golden outputs). citeturn0view0

> If adding PvP: place new code under `pogo_analyzer/pvp/` and expose it via feature‑flagged CLI options (e.g., `--mode pve|pvp` defaulting to `pve`).

---

## 8) Feature roadmap for the agent (suggested epics)

### 8.1 Add PvP scoring (feature‑flagged)

- Implement the formulas from `docs/pokemon_value_formulas_playbook.md` (see the separate playbook we generated in this project) to compute: Stat Product (SP), Move Pressure (MP), and `V_PvP`.  
- Add inputs for league (`--league GL|UL|ML`) and an optional path to pre‑scraped moves/species data (CSV/JSON).  
- Output a separate `pvp_scoreboard.csv` without changing PvE defaults.

### 8.2 PvE refinements (optional toggles)

- Energy‑from‑damage, relobby tax, and boss‑cluster weighting; expose via CLI flags and document in `README.md`.

### 8.3 Data updater (offline, optional command)

- New command `pogo-data-refresh` to fetch and normalize species/moves/learnsets into the schemas defined in the playbook.

### 8.4 Documentation & examples

- Add end‑to‑end examples in `docs/` showing CSV inputs → outputs for both PvE and PvP.

---

## 9) Coding standards & PR checklist

- **Style:** PEP8; type hints for public functions. Keep functions small and pure where possible.  
- **Docs:** Update `README.md` and `docs/` when adding flags or outputs. Include usage examples.  
- **Tests:** Cover new branches/flags. If outputs change, update golden CSVs with clear justification.  
- **Changelog:** Append concise entries to `CHANGELOG.md`.  
- **Performance:** If you change hot paths, run microbenchmarks and note any regressions in the PR description.
- **Commit hygiene:** Conventional commit style (feat:, fix:, docs:, chore:, refactor:, test:, perf:).

**PR acceptance checklist (copy into PR):**  

- [ ] All tests pass (`pytest`)  
- [ ] README/docs updated  
- [ ] No breaking changes to CLI defaults  
- [ ] Added/updated unit tests  
- [ ] Benchmarks checked (if relevant)  
- [ ] No secrets / licenses violations

---

## 10) Data sources (for the agent’s optional updater)

The project doesn’t ship live scrapers, but if you implement an **offline data refresh** tool, use these sources and **be respectful**:

- **Species stats/types & learnsets:** GO Hub Database pages (per Pokémon) — base stats, typing, and move pools (legacy badges included).  
- **Move stats:** GamePress PvP Fast/Charged pages, GO Hub move tables, and/or PvPoke move CSV exports.  
- **Rules & constants:** CPM tables (GamePress or GO Hub), type multipliers (GO standard), weather boost rules (Niantic Help Center).  
- **Meta references:** PvPoke rankings pages (for optional normalization/anti‑meta).  
Refresh weekly or on season/balance changes; obey robots.txt, back off on 429, and cache the last successful snapshot. (See the Implementation Playbook for schemas + links.)

---

## 11) Risk register & mitigations

- **Breaking user workflows:** Any change to default CSV columns or CLI behavior must be flagged as breaking and deferred to a major version.  
- **Data drift:** Stamp generated outputs with a `data_version` and `source_date` if you introduce scraped inputs.  
- **Scrape fragility:** Prefer structured downloads (CSV) over HTML scraping. Add schema validators.  
- **Performance regressions:** Benchmark large rosters; keep complexity linear in number of entries.  

---

## 12) Example agent prompts

- “Add a `--league` flag to the CLI; when set, compute PvP scores using pre‑scraped files in `data/` and write `pvp_scoreboard.csv`. Keep the PvE scoreboard as default and unmodified.”  
- “Introduce `--pve-energy-from-damage` (bool) and `--pve-relobby-phi` (float) and plumb them to the scoring functions; update README with examples.”  
- “Create `docs/pvp.md` with SP/MP formula summaries and command examples; include a link from the README.”  
- “Write tests for the new CLI flags: one golden CSV per mode, assert column sets and top‑N rows.”

---

## 13) Support info

- **Python:** 3.9+  
- **Primary command:** `pogo-raid-scoreboard` (see `--help`)  
- **Primary docs:** `README.md` and `docs/` (API and usage). citeturn0view0

---

### Final note

This guide is deliberately **constraint‑heavy** so the agent protects existing users while still making meaningful progress (PvP, data refresh tooling, and PvE refinements) in small, reviewable increments.
