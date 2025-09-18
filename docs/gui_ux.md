**PoGo Analyzer — Streamlit UX/UI Review and Redesign Proposal**

This document summarizes a practical UX/UI plan for the Streamlit GUI that wraps the PoGo Analyzer toolkit. It follows the goals and acceptance criteria in `ux-ui2.md` while preserving CLI defaults and contracts.

**Critique (current first pass)**
- Navigation: Tabs exist for Quick Check, Raid Scoreboard, PvP Scoreboard, Glossary, About. Missing a dedicated Config/Data view for environment defaults and files.
- Density and scanability: Tables render plainly; no inline score affordances or progressive filtering. Selecting rows for export is not obvious.
- Cognitive load: Advanced PvE/PvP toggles are present but mixed within the primary form; better grouping helps.
- Feedback: Quick Check returns stat inference and PvE/PvP numbers but lacks a unified “Raid Score” snapshot and action chips.
- Theming: Base tokens exist; chips and elevation styles are present but not consistently applied across views.

**Redesign (implemented)**
- Add “Data & Config” tab to adjust scoreboard environment defaults (session‑scoped) and centralize dataset guidance.
- Quick Check adds Target CP, Needs TM/Has Special Move, Mega Now/Soon, and Notes. Shows a “Raid Score” snapshot with tier and action chips.
- Raid Scoreboard view adds filters (score range, role, needs‑TM), row density toggle, progress bars for score, selection + CSV export, and full CSV/XLSX download buttons.
- Glossary refined into a searchable two‑column list for quick scanning.

**Wireframe (low‑fi)**
- Quick Check
  - Header
  - Basics (name, CP, Target CP, IVs, Variant/Lucky/BB/Observed HP, Needs TM/Has Special, Mega Now/Soon, Notes)
  - Species (optional base stats)
  - PvE (optional, with Advanced expander)
  - PvP (optional)
  - After submit: Stats card + Raid Score (Tier + Chips) + PvE/PvP sections
- Raid Scoreboard
  - Controls row: Preview | Density | Score range | Needs TM
  - Columns: Filters (role, search) | Table (progress column + selection) | Exports
- Data & Config
  - RAID_SCOREBOARD_* inputs + Apply button

**Component Inventory**
- Layout: `st.tabs`, `st.columns`, `st.container`, `st.divider`, `st.expander` (advanced only)
- Inputs: `st.selectbox`, `st.radio`, `st.checkbox`, `st.number_input`, `st.text_input`, `st.multiselect`, `st.file_uploader`
- Tables: `st.dataframe` with `st.column_config.ProgressColumn` for the score; `st.download_button`
- Feedback: `st.metric`, `st.info`, `st.success`, `st.error`, custom CSS chips via badges

**Design System (starter)**
- Typography: Base 14–15, section headers 20–24, dense table 12.
- Spacing: 4 / 8 / 12 / 16 / 24 / 32; cards use 16.
- Colors: primary `#3F7CEC`, success `#2FBF71`, warn `#FFB020`, error `#E5484D`.
- Chips: Rounded “badge” used for status (Shadow, Purified, Needs ETM, Build/Consider/Skip).
- Elevation: subtle `box-shadow: 0 6px 18px rgba(0,0,0,.10)` on cards.
- States: Empty—clear prompts; Loading—inline spinners; Errors—concise messages.

**Persona Playbook**
- Hardcore Raider Hannah: Upload/Generate → Filter Needs TM + Score ≥85 → Export shortlist (≤2 minutes).
- PvP Grinder Gabe: Quick Check → League + bait model → Compare to Target CP → Decide (clear Tier + PvP score).
- Returning Player Riley: Search name → Details (Move Needs) → Chip suggests ETM → Add note.
- Data Tinkerer Dana: Data & Config → Change output dir and CSV name → Generate → Download.

**Validation Plan**
- Analytics: Instrument button presses (Generate, Quick Check, Export) via Streamlit event counters. Track count/usage in session state.
- Usability: 5-task think‑aloud (one per persona). Success: ≥80% task completion without assistance.
- Accessibility: Keyboard focus through inputs and buttons; verify color contrast on dark backgrounds; test at 360px width.

**Backlog (P0/P1/P2)**
- P0: Quick Check Raid Score + chips; Scoreboard filters + exports; Data & Config tab; pve_tier export fix.
- P1: Best‑move autofill using normalized datasets for more species; CSV Excel conditional formatting; compare‑tray for 2–3 picks.
- P2: Shareable permalinks (serialize state to query); theme switcher (default/high‑contrast); optional AgGrid for richer tables.

This proposal preserves existing CLI contracts and adds GUI affordances behind optional controls. All new behavior is UI‑only and does not change default CSV columns.
