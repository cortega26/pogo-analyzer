# UX/UI Review & Persona-Driven Optimization Prompt for *PoGo Analyzer* Streamlit App

You are a **Senior UX/UI Engineer** tasked with improving the front-end of a Streamlit app that wraps the open-source **PoGo Analyzer** toolkit. The repo is here: https://github.com/cortega26/pogo-analyzer.

## Context (what the app does today)
- The core toolkit generates a **Raid value scoreboard** (grades Pokémon 1–100) and exports CSV/Excel; it also supports a **single-Pokémon quick check** that infers level from CP and can surface **PvE/PvP value metrics** without creating export files. See README for details.
- CLI name: `pogo-raid-scoreboard` with options for output location, preview limits, and environment-variable overrides.
- Quick check accepts species, base stats, IVs, and move descriptors; supports PvE assumptions (incoming DPS, defense) and PvP parameters (league caps, bait model, anti-meta, coverage factors, etc.).

## Objectives
1. **Make the interface intuitive for non-technical players while preserving power-user depth.**
2. **Accelerate decision-making**: which Pokémon should I power up, Elite TM, or build next?
3. **Reduce cognitive load** with clean information architecture, clear defaults, and progressive disclosure.
4. **Support quick “what-if” simulations** for move sets, IVs, CP targets, and weather/bonus toggles.
5. **Ensure responsive performance** on rosters of 200–2,000 entries; minimize reruns.

## Deliverables
- A written **UX/UI critique** of the current app (assume a first pass exists) and a **redesign proposal** with wireframe sketches (low-fi is fine).
- A **component inventory** for Streamlit (widgets, layout primitives) and any recommended community components.
- A **design system** starter: colors, spacing, typography, elevation, iconography, and state conventions.
- A **persona playbook** with flows and success metrics.
- A **validation plan** (lightweight usability tests + analytics).

---

## Primary Views to Design / Refine

### 1) **Roster Scoreboard**
**Goal:** Triage best raid investments at a glance.
- **Table** (pandas DataFrame or st.dataframe):
  - Columns (sample): Name, Form (Shadow/Mega), Role, IVs, **Raid Score (1–100)**, Needs Special Move (chip), Target CP, Notes.
  - Add sticky header, column resizing, sortable headers.
  - **Row density** toggle: Cozy / Compact.
  - **Conditional formats:** Green (≥90), Amber (75–89), Red (<75). Color-blind safe palette.
- **Filters / Facets (left sidebar):**
  - Role (DPS/Support), Type, Shadow/Mega, Needs TM?, Has Special Move?, Score range slider.
  - Include **“Only show builds above target CP”** toggle (if target CP is set).
- **Batch actions:**
  - Select rows to **export** (CSV/XLSX) and to add **bulk notes** or **priority tags**.
- **Details drawer (progressive disclosure):**
  - Breakdown: Baseline species strength, IV bonus, lucky cost savings, move requirements, mega availability, plus links to quick-check.

### 2) **Single Pokémon Quick Check**
**Goal:** Instant recommendation without exporting files.
- **Inputs group** (cards):
  - Pokémon name (autocomplete), Shadow/Mega toggles, IVs, observed CP, **target CP**.
  - Optional moves: fast/charge descriptors (name, power, energy, duration + STAB/weather flags).
- **Scenario toggles:**
  - PvE: incoming DPS, target defense, dodge factor.
  - PvP: league cap, bait model, anti-meta slider, energy/buff weight, coverage.
- **Output cards:**
  - **Raid Score** with tier badge (S/A/B/C), CP→Level inference, CPM, effective stats.
  - PvE rotation summary; PvP value snapshot across 0/1/2 shields.
  - **Action chips:** “Needs Elite TM”, “Under target CP”, “Worth building now”.

### 3) **Data Refresh & Config**
- Surface environment variables mapped to UI controls (output dir, file names, preview rows).
- “Advanced” accordion for enhanced defaults bundle and experimental flags.

---

## Information Architecture & Layout

- Use **3-panel layout** on wide screens: left **Filters**, center **Primary content**, right **Context panel** (details, notes, history). Collapse to 2 panels on medium; single column on mobile.
- Keep **primary call-to-action** persistent: “Run Scoreboard” / “Quick Check”.
- **Progressive disclosure**: Hide advanced PvE/PvP flags behind accordions with summaries (“3 advanced toggles active”).

---

## Design System (starter)

- **Typography:** Inter or Source Sans 14–15 base; 20–24 for section headers; 12 for dense table.
- **Spacing scale:** 4/8/12/16/24/32. Use 16px base padding for cards/sections.
- **Color tokens:** `success`, `warning`, `danger`, `info`, `muted`. Ensure WCAG AA contrast.
- **Status chips:** Shadow, Mega, Needs TM, Exclusive Move owned.
- **Icons:** Simple line icons for role/type, info tooltips for formulas.
- **Empty states:** Clear prompts and example inputs.
- **Loading states:** Skeleton rows for table; inline spinners for cards.

---

## Streamlit Implementation Notes

- Prefer **`st.columns` + `st.container`** for grid; avoid overuse of `st.expander` for primary content.
- Use **`st.cache_data` / `st.cache_resource`** strategically to avoid recomputing formulas for unchanged inputs.
- For large tables, render **server-side pagination** or chunked `st.dataframe` with **row virtualization**.
- Encapsulate computation in pure functions (wrapping existing library) to keep **UI reactive and testable**.
- Provide a **download button** for CSV/Excel; mirror CLI and environment variable semantics.
- Add **help tooltips** on advanced flags with links to docs.
- Offer **keyboard shortcuts** (via `st-keyup` custom component or `streamlit-shortcuts`) for “Run”, “Export”.

---

## Personas & Flows (simulate in review)

1) **Hardcore Raider Hannah**
   - **Goal:** Optimize next 5 high-ROI power-ups before a raid weekend.
   - **Flow:** Upload roster → Filter Needs TM + ≥85 score → Sort by ROI → Export shortlist.
   - **Success:** Finds 5 candidates in <2 minutes; exports CSV; no advanced flags touched.

2) **PvP Grinder Gabe**
   - **Goal:** Evaluate if specific IV spread is worth building for GL/UL.
   - **Flow:** Quick Check with league cap + bait model → Compare to target CP → Decide.
   - **Success:** Clear tier decision and PvP score snapshot without leaving the view.

3) **Returning Player Riley**
   - **Goal:** Understand why a favorite mon is graded low and what to fix.
   - **Flow:** Search name → Open details drawer → Read breakdown (move issue) → Action chip suggests **“Needs Elite TM”**.
   - **Success:** Understands next step; adds note/reminder.

4) **Data Tinkerer Dana**
   - **Goal:** Batch export with custom filenames and output dir.
   - **Flow:** Config view → Set output dir & disable Excel → Run → Download CSV.
   - **Success:** No errors; settings persist across session.

---

## Visual & Interaction Heuristics Checklist

- Clear **visual hierarchy** (title > section > card > caption).
- Keep **decision metrics above the fold** (Score, Tier, Needs TM).
- **One primary action per view**; secondary actions as links or muted buttons.
- **Consistent chip styles** for states; avoid mixing shape/size.
- **Mobile first**: test 360px width; ensure touch-friendly targets (≥44px).
- **Color-blind safe**; don’t rely on color alone—add icons/labels.
- **Performance**: initial render <1.5s; interactions <300ms when cached.

---

## Analytics & Validation

- Enable **Streamlit app analytics** to track views and engagement.
- Instrument key events: Run Scoreboard, Export, Quick Check, Filter change, Persona success goals.
- 5-task **usability test** with think-aloud; success if ≥80% complete without moderator help.
- Post-launch: add **feedback widget** and collect NPS (“How useful was this score?”).

---

## Acceptance Criteria (Definition of Done)

- Scoreboard view with filters, conditional formatting, and details drawer.
- Quick Check view producing a score, tier, and action chips in <2s on cached data.
- Settings persisted during session; download buttons for CSV/XLSX.
- Accessible color tokens; dark mode friendly; keyboard navigation works.
- Persona scenarios pass the success metrics above.

---

## Nice-to-Haves

- **Comparison tray** to pin 2–3 Pokémon for side-by-side stats.
- **Shareable permalinks** (serialize inputs to query string).
- **Theme switcher** with 2 presets (Default / High-contrast).

---

## What to Hand Back

- Wireframes (PNG or Figma link), component list, style tokens, and a short Loom walkthrough.
- A prioritized backlog (P0/P1/P2) with estimates.
