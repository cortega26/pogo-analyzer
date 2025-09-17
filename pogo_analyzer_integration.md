# 🚀 Implementation Prompt — Integrate CP→Level inference + PvE/PvP scoring into **pogo-analyzer**

**Repository:** `https://github.com/cortega26/pogo-analyzer`  
**Objective:** Add precise CP→Level inference (from CP+IVs+flags), expose effective stats \(A,D,H\), and implement PvE+PvP value scoring as defined in `pokemon_value_formulas.md`. Provide a clean Python API, CLI options, docs, and tests.

> The repo already exposes a CLI (`pogo-raid-scoreboard`) and library helpers; keep code idiomatic and match existing style and test patterns. README mentions a `PokemonRaidEntry` dataclass and helpers like `calculate_raid_score` and `build_entry_rows`. Use similar patterns and keep public API small.

---

## 0) Inputs you have to work with

1) **Ground-truth spec**: the file provided `pokemon_value_formulas.md` (contains:
   - CP formula with CPM, Shadow/BB handling, and flooring
   - Robust level inference via CP+IVs (+ HP disambiguation)
   - Effective stats \(A,D,H\)
   - Unified per-hit damage formula (STAB, weather, typing)
   - PvE scoring: optimized rotation DPS + TDO → \(V_{PvE}\)
   - PvP scoring: stat product + move-pressure → \(V_{PvP}\)
2) Repo entry points and docs:
   - **README** explains the CLI, library import points, and where raid entries live. Use its style for examples and CLI help text.
   - **Dataclasses & helpers** are referenced in README (`pogo_analyzer/data/raid_entries.py`, `calculate_raid_score`, etc.). Keep new APIs consistent.

---

## 1) Tasks (in this exact order)

### A) Create a feature branch
- Branch: `feat/cp-level-and-pve-pvp-scoring`
- Add a small CHANGELOG entry.

### B) Vendor the formulas doc
- Add `docs/formulas.md` by copying my `pokemon_value_formulas.md` verbatim (normalize headings for MkDocs/GitHub rendering).

### C) Library: new modules & public API
Create a small, focused API inside `pogo_analyzer/`:

1. **`pogo_analyzer/cpm_table.py`**
   - Constant `CPM: dict[float, float]` for levels `{1, 1.5, …, 50, 51}`.
   - Helper `get_cpm(level: float) -> float`.

2. **`pogo_analyzer/formulas.py`**
   - `infer_level_from_cp(...) -> tuple[float,float]`  
     (robust search, BB handling, HP disambiguation).
   - `effective_stats(...) -> tuple[float,float,int]`
   - `damage_per_hit(...) -> int`

3. **`pogo_analyzer/pve.py`**
   - FastMove/ChargeMove dataclasses.
   - `rotation_dps(...) -> float`
   - `estimate_ehp(...) -> float`
   - `pve_value(...) -> float`
   - `compute_pve_score(...) -> dict`

4. **`pogo_analyzer/pvp.py`**
   - Stat product, move pressure, value functions.
   - `compute_pvp_score(...) -> dict`

All importable like:
```python
from pogo_analyzer.formulas import infer_level_from_cp, effective_stats
from pogo_analyzer.pve import compute_pve_score
from pogo_analyzer.pvp import compute_pvp_score
```

### D) CLI integration
- Extend `pogo-raid-scoreboard` with new flags for Pokémon quick check:
  - `--species`, `--base-stats`, `--cp`, `--ivs`, `--shadow`, `--bb`, `--observed-hp`
  - PvE flags: `--fast`, `--charge`, `--weather`, `--target-defense`, `--alpha`
  - PvP flags: `--league-cap`, `--beta`, `--mp-ref`, `--sp-ref`, `--bait-prob`
- Print inferred Level, CPM, A/D/H, then PvE and/or PvP values depending on flags.

### E) Docs
- Add `docs/formulas.md` and `docs/cli.md` (CLI examples).
- Update `README.md` with CP→Level & PvE/PvP quick start.

### F) Tests
- `test_formulas_level_inference.py`
- `test_pve_rotation.py`
- `test_pvp_value.py`
- Ensure pytest passes.

### G) Benchmarks (optional)
- Add benchmarks for rotation DPS.

---

## 2) Design & correctness requirements

- Numerical fidelity (floors, multipliers, etc.)
- Performance (efficient level search, bounded DPS cycle search)
- API ergonomics (small, pure functions; no heavy deps)
- Non-breaking changes to existing CLI

---

## 3) Acceptance criteria

1) Tests and CI pass.  
2) CLI examples work (Hydreigon PvE, Azumarill PvP).  
3) README updated.  
4) Public API works as documented.

---

## 4) Implementation notes

- Prefer dataclasses, pure functions, type hints.
- Add doctests where useful.
- Update pyproject.toml only if needed.

---

## 5) Git commands

```bash
git checkout -b feat/cp-level-and-pve-pvp-scoring
# add code, docs, tests
pytest -q
git add .
git commit -m "feat: CP→Level inference + PvE/PvP scoring"
git push -u origin feat/cp-level-and-pve-pvp-scoring
```

---

## 6) Files to read first

- `pokemon_value_formulas.md`
- `README.md`
- `pogo_analyzer/` package
- `tests/`

---

## 7) Where this spec lives

- `docs/formulas.md`  
- `docs/cli.md`  
- `pogo_analyzer/formulas.py`, `pogo_analyzer/pve.py`, `pogo_analyzer/pvp.py`, `pogo_analyzer/cpm_table.py`  
- `tests/test_*.py`

---

**End of prompt.**
