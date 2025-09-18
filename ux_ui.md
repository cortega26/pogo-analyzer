# UX/UI Senior Engineer Prompt & Recommendations for PoGo Analyzer

This file contains the fully filled Option 2 prompt, tailored to the PoGo Analyzer Streamlit app.

---

## 1) Executive Summary (≤7 bullets)
- Make the app **task-first**: split “Quick Check” vs “Scoreboards” into primary tabs; keep advanced tuning in clearly labeled expanders.  
- Adopt a **4/8/12/16/24 spacing scale**, a compact **data-first layout** (wide mode + 2:1 grid), and consistent H1/H2/H3 to reduce scanning time.  
- Replace overused dropdowns with **radio/segmented controls** for ≤6 choices; use **searchable selects** for long lists (species, moves).  
- Standardize **empty/loading/error** patterns and **result “cards”** (grade, role, CP/IVs, must-have move flags) to improve recognition.  
- Add **sticky filter bar** and **inline explanations** (helper text + tooltips) mirroring your CLI wording for transparency.  
- Ship a **theme token set** (primary/neutral/semantic), **type scale**, and **number formatting rules** so charts/tables feel cohesive.  
- Quick performance wins: cache data transforms, memoize species/moves, and defer heavy calcs until “Run” is pressed.

---

## 2) Prioritized Fix List

| Issue | Recommendation | Why it helps (heuristic) | Effort | Impact | Example |
|---|---|---|---|---:|---|
| Mixed discovery of Quick Check vs Scoreboards | Make **tabs**: “Quick Check”, “Raid Scoreboard”, “PvP Scoreboard” | Matches user mental model; reduces navigation cost | M | 5 | Tabs with task names |
| Long selects (species/moves) | Use **`st.selectbox` with `st.text_input` filter**, remember last picks | Recognition over recall; speeds repeat use | S | 4 | Searchable species picker |
| Advanced flags overwhelm | **Expander**: “Advanced tuning”, grouped by PvE/PvP | Progressive disclosure | S | 5 | `with st.expander("PvP advanced"):` |
| Hard-to-scan results | **Result cards** with badges (Shadow, Needs TM, Special Move) | Visibility of system status | M | 5 | Card with badges |
| Inconsistent spacing/typography | Add **theme + spacing + type scale** | Aesthetic & minimalist design | S | 4 | Theme JSON below |
| No standard empty/loading/error | Add **info/warn/error** patterns | Error prevention & recovery | S | 3 | `st.info("No results…")` |
| Filters not sticky | **Sticky header** with filters | User control & efficiency | M | 4 | CSS + container |
| Performance on reruns | **`st.cache_data`** for species/moves; **`st.memo`** for transforms | Response time | S | 4 | Caching snippet |
| Explainer text fragmented | **Helper text + tooltips** mirroring CLI descriptions | Match between system & real world | S | 3 | `st.help("…")` |
| Dense tables | **Iconography + numeric formatting** + column priorities | Reduce cognitive load | M | 4 | Format % and DPS |

---

## 3) Page & Layout Pass
- **Layout grid:** `wide` mode; sticky **filter bar** above content; main area uses `st.columns([2,1])` on desktop; stack on mobile.  
- **Spacing scale:** `4, 8, 12, 16, 24` px steps (apply to gaps/paddings).  
- **Hierarchy:**  
  - H1: Page title (e.g., “PoGo Analyzer”)  
  - H2: Tab titles (Quick Check / Raid Scoreboard / PvP Scoreboard)  
  - H3: Section titles (Inputs, Results, Advanced, Notes)  
- **Progressive disclosure:** Expander groups for **Advanced PvE** and **Advanced PvP** flags.  

---

## 4) Components & Patterns
- Short lists → **`st.radio`** / segmented; long lists → **`st.selectbox`** + search.  
- Add **helper text** beneath controls that reuse CLI help text.  
- **Empty state:** “No results for current filters—try removing league cap or widening CP range.”  
- **Loading state:** `st.spinner("Scoring your build…")`  
- **Error state:** `st.error("Couldn’t parse move descriptor…")`  

---

## 5) Visual System

**Theme tokens (WCAG-conscious):**
```python
st.set_page_config(page_title="PoGo Analyzer", layout="wide")
st.markdown("""
<style>
:root{
  --space-1:4px;--space-2:8px;--space-3:12px;--space-4:16px;--space-5:24px;
  --radius:12px; --elev: 0 4px 14px rgba(0,0,0,.08);
}
</style>
""", unsafe_allow_html=True)
st.theme = {
  "primaryColor": "#3F7CEC",
  "backgroundColor": "#0F1116",
  "secondaryBackgroundColor": "#171a21",
  "textColor": "#E6E6E6",
  "font": "Inter"
}
```
**Type scale:** 12/14/16/20/24/32; headings bold, body regular, line-height 1.4–1.6.  
**Semantic colors:** success `#2FBF71`, warn `#FFB020`, error `#E5484D`.

---

## 6) Charts & Data Density
- One chart per question.  
- Always label axes, format numbers (`1,234`, `35.7%`, units like *DPS*, *TDO*).  
- Use **legends** only when >1 series; otherwise, inline labels.  
- Prefer **Altair** for interactive charts with tooltips.  

---

## 7) Microcopy & IA
- Buttons: **“Run Quick Check”**, **“Generate Raid Scoreboard”**, **“Generate PvP Scoreboard”**.  
- Badges: **Shadow**, **Needs TM**, **Has Special Move**, **Best Buddy**.  
- Helper text examples:  
  - “**Level inference**: we estimate level & CPM from CP + IVs.”  
  - “**Weather**: pass global weather or override per move (‘weather=true’).”  

---

## 8) Performance & State
- `@st.cache_data` for species/moves dataset and normalized data.  
- `@st.memo` for score computations keyed by input tuple.  
- Use a **“Run” button** to avoid recomputing on every keystroke.  
- Store inputs in `st.session_state` for wizard-like flows.  

---

## 9) Accessibility Checklist
- Contrast ≥ 4.5:1 for body text; ≥ 3:1 for large headings.  
- Focus order: search → primary filters → Run → results.  
- All click targets ≥ 44px; keyboard reachable.  
- Do not encode meaning by color alone—use badges + icons + text.  

---

## 10) Persona Walkthroughs

**Analyst Alice (new user)**  
Goal: Verify Hydreigon. Path: Quick Check. Friction: Unsure about “special move.” Fix: Move checklist with ✅/**!**.  

**Manager Max (time-poor)**  
Goal: “What should I power up next for raids?” Path: Raid Scoreboard. Friction: Too many flags. Fix: Defaults + Advanced expander.  

**Expert Eve (power user)**  
Goal: Tweak PvP assumptions. Path: PvP Scoreboard. Friction: Hard to recall params. Fix: Inline tooltips with examples.  

---

## 11) Wireframe (ASCII)

```text
[ Sticky Header ]
┌────────────────────────────────────────────────────────────────────────────┐
│ H1: PoGo Analyzer                  [Run Quick Check]  [Generate Scoreboards]│
│ Filters: [Species 🔎] [CP] [IVs] [Shadow ☐] [Has Special Move ☐] [Best Buddy ☐]│
│        [League: ☐ 1500 ☐ 2500 ☐ 10000] [Weather ☐] [Target CP]              │
└────────────────────────────────────────────────────────────────────────────┘

Tabs: [ Quick Check ] [ Raid Scoreboard ] [ PvP Scoreboard ]

(Quick Check)
┌──────────────────────────────┬──────────────────────────────────────────────┐
│ H3: Results (card)           │ H3: Notes & Explainers                      │
│  • Grade: 92/100  [Dark DPS] │  • Required move? Brutal Swing:  ✅         │
│  • Inferred Level: 34.5      │  • Why this score: base + IV + move + mega  │
│  • Must-have move: ✅         │    availability                            │
│  • Badges: Shadow, Needs TM  │  • Links: Data & PvP assumptions            │
└──────────────────────────────┴──────────────────────────────────────────────┘

(Raid Scoreboard / PvP Scoreboard)
┌────────────────────────────────────────────────────────────────────────────┐
│ [Download CSV] [Download XLSX] [Search] [Sort: Raid Score ▼]               │
│ Table: Name | Role | Score | Must-Have Move | Target CP | Notes | Badges   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 12) Streamlit-Ready Code Snippets

### A) App shell, tabs, sticky filters
```python
# see full code snippet in deliverable
```

### B) Advanced groups with expanders
```python
# see full code snippet in deliverable
```

### C) Results card with badges
```python
# see full code snippet in deliverable
```

### D) Standard empty/loading/error patterns
```python
# see full code snippet in deliverable
```

### E) Caching datasets & transforms
```python
# see full code snippet in deliverable
```

### F) Scoreboards with downloads
```python
# see full code snippet in deliverable
```

---
