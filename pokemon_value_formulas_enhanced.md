# Pokémon GO Value Calculation Framework (Enhanced)

This document specifies a **complete, implementable** framework to score Pokémon for **PvE** (raids/gyms) and **PvP** (trainer battles), with optional **fine‑tuning knobs** to reflect practical nuances (e.g., baiting, breakpoints, energy-from-damage, role fit). It is designed to drop into code directly.

---

## 0) Preliminaries & Notation

- **Base stats**: \\\( (A_{\text{base}}, D_{\text{base}}, S_{\text{base}}) \\\)
- **IVs**: \\\( (\text{iv}_A, \text{iv}_D, \text{iv}_S) \\\)
- **Shadow flag**: \\\( \text{sh} \in \{0,1\} \\\)
- **Purified flag**: \\\( \text{pu} \in \{0,1\} \\\) *(used for move availability like Return; no stat multiplier)*
- **Best Buddy flag**: \\\( \text{bb} \in \{0,1\} \\\)
- **Combat Power Multiplier (CPM)**: \\\( c(L) \\\) for \\\( L \in \{1, 1.5, \dots, 50\} \\\); Best Buddy grants **effective +1 level** in CPM lookup.
- **League context (PvP)**: \\\( \mathcal{L} \in \{\text{GL},\text{UL},\text{ML}\} \\\). Use PvP move stats in PvP and PvE move stats in PvE.

**Shadow multipliers** (applied pre-CPM):
- \\\( m_A^{\text{sh}} = 1.2^{\text{sh}} \\\)
- \\\( m_D^{\text{sh}} = 0.83^{\text{sh}} \\\)

**Pre-CPM stats**:
- \\\( A_0 = (A_{\text{base}} + \text{iv}_A)\cdot m_A^{\text{sh}} \\\)
- \\\( D_0 = (D_{\text{base}} + \text{iv}_D)\cdot m_D^{\text{sh}} \\\)
- \\\( S_0 = (S_{\text{base}} + \text{iv}_S) \\\)

> **Purified note:** Purified has no stat multiplier. Its effect is **move availability** (e.g., *Return*) and potential IV changes when purifying. Reflect this in moveset enumeration, not in stats.

---

## 1) Level Inference from CP

**CP formula** (BB handled via CPM lookup at \\\( L+\mathbf{1}\{\text{bb}=1\} \\\)):
\\\[
\text{CP}(L,\text{bb}) = \left\lfloor
\frac{A_0\cdot \sqrt{D_0}\cdot \sqrt{S_0}\cdot \big(c(L+\mathbf{1}\{\text{bb}=1\})\big)^2}{10}
\right\rfloor
\\\]

Given observed \\\( \text{CP}_{\text{obs}} \\\): search \\\( L\in\{1,1.5,\dots,50\} \\\) and pick the \\\( L \\\) such that \\\( \text{CP}(L,\text{bb})=\text{CP}_{\text{obs}} \\\). If multiple candidates exist, use

\\\[ \text{HP}_{\text{obs}} = \left\lfloor S_0 \cdot c(L+\mathbf{1}\{\text{bb}=1\}) \right\rfloor \\\]

to disambiguate.

---

## 2) Effective Stats (post level inference)

Let \\\( L^\* \\\) be the inferred level and \\\( c^\* = c(L^\*+\mathbf{1}\{\text{bb}=1\}) \\\).

\\[
A = A_0 \cdot c^\*, \quad
D = D_0 \cdot c^\*, \quad
H = \left\lfloor S_0 \cdot c^\* \right\rfloor.
\\]

---

## 3) Move Multipliers & Damage

- **STAB:** \\\( m_{\text{stab}} = 1.2 \\\) if move type matches Pokémon typing; else 1.0.
- **Weather (PvE only):** \\\( m_{\text{weather}} = 1.2 \\\) if boosted; else 1.0. *(Set to 1.0 in PvP.)*
- **Type effectiveness:** \\\( m_{\text{type}} \in \{0.625,\,1.0,\,1.6\} \\\) (apply twice for double effectiveness or double resistance).

**Damage per hit** for a move \\\( x \in \{\text{fast}, \text{charge}\} \\\):
\\[
\text{Damage}_x = \left\lfloor 0.5 \cdot P_x \cdot \frac{A}{D_{\text{def}}} \cdot
\big(m_{\text{stab}}\cdot m_{\text{weather}} \cdot m_{\text{type}}\big) \right\rfloor + 1.
\\]

Use **PvE** or **PvP** move data appropriately:
- PvE: `power_pve`, `duration_s`, `energy_delta_pve` (fast: +, charge: –).
- PvP: `power_pvp`, `turns` (each turn = 0.5s), `energy_delta_pvp`.

---

## 4) PvE Value

### 4.1 DPS (rotation-based, energy-constrained)
Let fast move have \\\( t_f \\\) (s) and energy gain \\\( e_f>0 \\\), charge moves \\\( c \\\) have duration \\\( t_c \\\) and costs \\\( E_c>0 \\\). Solve:

\\[
\text{DPS}=\max_{n_f,\{n_c\}}\;
\frac{n_f\cdot \text{Damage}_f + \sum_c n_c\cdot \text{Damage}_c}{n_f\cdot t_f + \sum_c n_c\cdot t_c}
\quad
\text{s.t.}\;\; n_f\cdot e_f + E_{\text{taken}} \ge \sum_c n_c\cdot E_c.
\\]

**Energy from damage (optional):** In PvE, set \\\(E_{\text{taken}} \approx \rho_E \cdot \frac{\text{HP lost}}{1} \\\) with default \\\( \rho_E = 0.5 \\\) (≈ 1 energy per 2 HP lost). If disabled, use \\\(E_{\text{taken}}=0\\\).

### 4.2 Durability & Output
- **Incoming DPS:** \\\( \text{DPS}_{\text{in}}\\\) (estimated from boss moves or scenario).
- **Effective HP:** \\\( \text{EHP} \approx H \cdot \frac{D}{D_{\text{tar}}} \\\) (choose \\\( D_{\text{tar}} \\\) consistent with scenario).
- **Time to Faint:** \\\( \text{TTF} = \text{EHP} / \text{DPS}_{\text{in}} \\\)
- **Total Damage Output:** \\\( \text{TDO} = \text{DPS}\cdot \text{TTF} \\\)

**Relobby / swap downtime (optional):** Apply \\\( \text{RelobbyPenalty} = \exp(-\phi \cdot \text{TDO}) \\\) or subtract fixed downtime per faint to reduce effective DPS/TDO when fainting often.

### 4.3 PvE Score
\\[
V_{\text{PvE}} = \text{DPS}^{\alpha}\cdot \text{TDO}^{1-\alpha}, \quad \alpha \in [0.5,\,0.66].
\\]

**Boss weighting (optional):** For clusters \\\( j \\\) with weights \\\( w_j \\\), compute \\\( V_{\text{PvE,weighted}} = \sum_j w_j \cdot V_{\text{PvE}}^{(j)} \\\).

---

## 5) PvP Value

### 5.1 Stat Product (Bulk)
\\[
\text{SP} = A\cdot D\cdot H, \qquad \text{SP}_{\text{norm}} = \frac{\text{SP}}{\max(\text{SP}\ \text{over reference set in }\mathcal{L})}.
\\]
Use a **league-specific** reference set (eligible species/forms and typical caps).

### 5.2 Move Pressure (Offense & Shield Dynamics)

**Fast Move Pressure (FMP):** with PvP turns \\\(u_f\\\) (each 0.5s) and energy \\\(e_f\\\):
\\[
\text{FMP} = \frac{\text{Damage}_f}{0.5\cdot u_f} \;+\; \kappa \cdot \frac{e_f}{0.5\cdot u_f}
\quad (\kappa \ge 0).
\\]

**Charge Move Pressure (CPP):**
- For each charge move \\\( c \\\), define a **rate** \\\( r_c \\\) (expected uses per time window or per 100 energy generated by your fast move), and **buff EV**:
\\[
\text{BuffEV}_c = \sum_k \Delta\text{stage}_k \cdot \Pr_k
\quad\Rightarrow\quad
\text{CPP}_c = r_c \cdot \big(\text{Damage}_c + \lambda \cdot \text{BuffEV}_c\big).
\\]
- If two charge moves \\\( (c_{\text{low}},c_{\text{high}}) \\\) exist, incorporate **baiting**:
\\[
\text{CPP}_{\text{pair}} = p_{\text{bait}}\cdot \text{CPP}_{\text{high}} + (1-p_{\text{bait}})\cdot \text{CPP}_{\text{low}}.
\\]

**Move Pressure aggregate:**
\\[
\text{MP} = \text{FMP} + \max\big(\max_c \text{CPP}_c,\, \text{CPP}_{\text{pair}}\big), \qquad
\text{MP}_{\text{norm}} = \frac{\text{MP}}{\max(\text{MP}\ \text{in meta of }\mathcal{L})}.
\\]

**Shield-scenario blend (optional):** Compute \\\( V_{0s}, V_{1s}, V_{2s} \\\) with different \\\( p_{\text{bait}} \\\) and \\\( r_c \\\) assumptions, then
\\[
\text{MP}_{\text{blend}} = \omega_0 \text{MP}_{0s} + \omega_1 \text{MP}_{1s} + \omega_2 \text{MP}_{2s},\ \ \sum\omega_i=1,
\]
and use \\\( \text{MP}_{\text{blend}} \\\) in place of \\\( \text{MP} \\\).

### 5.3 PvP Score
\\[
V_{\text{PvP}} = (\text{SP}_{\text{norm}})^{\beta}\cdot (\text{MP}_{\text{norm}})^{1-\beta},
\qquad \beta \in [0.5,\,0.55].
\\]

---

## 6) Fine‑Tuning Add‑Ons (Optional Modifiers)

These modifiers are **toggleable**. Apply them as multiplicative factors to the base scores unless otherwise noted.

### 6.1 Breakpoint Awareness (PvE & PvP)
Evaluate fast/charge damage vs. reference \\\( D_{\text{ref}} \\\) (or common targets). Reward hitting breakpoints:
\\[
\text{BP}_{\text{bonus}} = \gamma \cdot \#\{\text{breakpoints hit across reference set}\},
\quad V \leftarrow V\cdot (1+\text{BP}_{\text{bonus}}).
\\]

### 6.2 CMP / Initiative Bonus (PvP)
If ties occur, higher Attack acts first. Give a small bonus for high-Attack percentiles in league \\\( \mathcal{L} \\\):
\\[
\text{CMP}_{\text{bonus}}=\eta \cdot \mathbf{1}\{A \ge \text{percentile}_p(A\,|\,\mathcal{L})\},
\quad V_{\text{PvP}} \leftarrow V_{\text{PvP}}\cdot (1+\text{CMP}_{\text{bonus}}).
\\]

### 6.3 Coverage / Typing Score (Both)
Estimate frequency of neutral or SE hits across a **target set** \\\( \mathcal{T} \\\). Let
\\[
\text{Coverage}=\frac{\#\{\text{neutral or SE matchups in }\mathcal{T}\}}{|\mathcal{T}|},
\quad V \leftarrow V\cdot \big(1+\theta\cdot(\text{Coverage}-0.5)\big).
\\]

### 6.4 Moveset Availability Penalty (Both)
Penalize hard-to-access moves (legacy/elite TM/event-only):
\\[
V \leftarrow V\cdot (1-\delta_{\text{availability}}),\ \ \delta_{\text{availability}}\in[0,\,0.1].
\\]

### 6.5 PvE Dodge / Downtime (PvE)
- **Dodge model:** reduce \\\( \text{DPS}_{\text{in}} \\\) during charged windows by factor \\\( \rho_{\text{dodge}} \\\) but subtract missed fast cycles.
- **Relobby tax:** apply exponential penalty \\\( \exp(-\phi\cdot \text{TDO}) \\\) or simulate fixed downtime per faint.

### 6.6 PvP Role Fit (PvP)
Compute \\\( V_{\text{lead}}, V_{\text{swap}}, V_{\text{closer}} \\\) with different weights:
- **Lead:** favor fast DPT and shield pressure (early shields up).
- **Safe-swap:** favor neutrality and spam.
- **Closer:** favor DPE and nukes (shields down).
Report all three or use \\\( V_{\text{role}} = \max \\\).

### 6.7 Anti‑Meta Bonus (PvP)
Given a top‑N meta set \\\( \mathcal{M} \\\), let
\\[
\text{AntiMeta} = \frac{\#\{\text{favored matchups vs }\mathcal{M}\}}{|\mathcal{M}|},\quad
V_{\text{PvP}} \leftarrow V_{\text{PvP}}\cdot (1+\mu\cdot \text{AntiMeta}).
\\]

---

## 7) Defaults & Tunables (JSON‑like)

```json
{
  "shared": {
    "gamma_breakpoint": 0.03,
    "eta_cmp": 0.02,
    "theta_coverage": 0.05,
    "availability_penalty": { "standard": 0.00, "legacy": 0.02, "elite_tm": 0.04, "event_only": 0.03 }
  },
  "pve": {
    "alpha": 0.6,
    "enable_energy_from_damage": true,
    "rho_energy_from_damage": 0.5,
    "relobby_phi": 0.08,
    "dodge": { "enabled": false, "rho_dodge": 0.4 },
    "boss_weights": { "dragon": 0.25, "flying": 0.20, "double_rock_weak": 0.10, "other": 0.45 }
  },
  "pvp": {
    "beta": 0.52,
    "kappa_fast_energy_weight": 1.0,
    "lambda_buff": 0.6,
    "shield_weights": [0.2, 0.5, 0.3],
    "bait": { "a": 0.4, "b": -0.1, "c": 0.35, "d": 0.0 },  // p_bait = sigmoid(a*EPT + b*DPT + c*Shields + d)
    "mu_anti_meta": 0.08,
    "cmp_attack_percentile": 0.7
  }
}
```

---

## 8) Pseudocode (End‑to‑End)

**Inputs:** base stats, IVs, flags (shadow, purified, best buddy), observed CP/HP (optional), CPM table, move data (PvE & PvP).

```pseudo
function infer_level(baseA, baseD, baseS, ivA, ivD, ivS, CP_obs, HP_obs?, isShadow, isBB):
    A0 = (baseA + ivA) * (1.2 if isShadow else 1.0)
    D0 = (baseD + ivD) * (0.83 if isShadow else 1.0)
    S0 = (baseS + ivS)
    for L in [1, 1.5, ..., 50]:
        c_eff = CPM[L + (1 if isBB else 0)]
        CP_calc = floor(A0 * sqrt(D0) * sqrt(S0) * c_eff^2 / 10)
        if CP_calc == CP_obs:
            if HP_obs is None: return (L, c_eff)
            HP_calc = floor(S0 * c_eff)
            if HP_calc == HP_obs: return (L, c_eff)
    return argmin_L |CP_calc - CP_obs|  // fallback

function effective_stats(A0, D0, S0, c_eff):
    A = A0 * c_eff; D = D0 * c_eff; H = floor(S0 * c_eff); return (A,D,H)
```

**Damage helpers** (context-aware PvE/PvP move stats, and multipliers):
```pseudo
function damage_per_hit(P, A, D_def, m_stab, m_weather, m_type):
    return floor(0.5 * P * (A / D_def) * (m_stab * m_weather * m_type)) + 1
```

**PvE rotation solver (with optional energy-from-damage & relobby):**
```pseudo
function pve_score(attacker, boss, config):
    // Build per-move damages with PvE stats and multipliers (STAB, weather, type)
    dmg_fast = damage_per_hit(P_fast_pve, A, D_boss, m_stab_f, m_weather, m_type_f)
    dmg_chg[c] = damage_per_hit(P_c_pve, A, D_boss, m_stab_c, m_weather, m_type_c)

    // Optimize over integer counts n_f and n_c subject to energy
    best_dps = 0
    for feasible combos (n_f, n_c[...]) respecting n_f*e_f + E_taken >= sum(n_c * E_c):
        time = n_f * t_f + sum(n_c * t_c)
        dmg  = n_f * dmg_fast + sum(n_c * dmg_chg[c])
        dps  = dmg / time
        best_dps = max(best_dps, dps)

    // Durability & TDO
    EHP = H * (D / D_tar)
    TTF = EHP / DPS_in
    TDO = best_dps * TTF

    // Optional relobby/dodge penalties
    if config.relobby.enabled: TDO *= exp(-phi * TDO)
    // Final PvE score
    V = best_dps^alpha * TDO^(1 - alpha)
    return V
```

**PvP move pressure and score (with shields & bait blending):**
```pseudo
function pvp_score(attacker, league_meta, config):
    // Bulk: Stat Product normalized to league reference
    SP = A * D * H
    SP_norm = SP / max_SP_in_league

    // Fast move pressure
    FMP = (dmg_fast / (0.5 * u_f)) + kappa * (e_f / (0.5 * u_f))

    // Charge move pressure for each charge move c
    for c in charges:
        BuffEV_c = sum(delta_stage_k * prob_k over c effects)
        CPP_c    = r_c * (dmg_c + lambda * BuffEV_c)

    CPP_pair = p_bait * CPP_high + (1 - p_bait) * CPP_low  // if two charges
    MP = FMP + max(max_c CPP_c, CPP_pair)
    MP_norm = MP / max_MP_in_meta

    // Scenario blending (0/1/2 shields) if enabled
    if config.blend_shields:
        MP_norm = w0*MP0 + w1*MP1 + w2*MP2

    V = (SP_norm)^beta * (MP_norm)^(1 - beta)

    // Optional post-modifiers: CMP, coverage, anti-meta, etc.
    if config.cmp.enabled and A >= percentile(A, p): V *= (1 + eta_cmp)
    if config.coverage.enabled: V *= (1 + theta * (coverage(attacker) - 0.5))
    if config.antimeta.enabled: V *= (1 + mu * anti_meta_rate(attacker, league_meta_topN))
    return V
```

---

## 9) Implementation Notes & Guidance

- **Data separation:** Always use PvE move stats for PvE and PvP move stats for PvP. Disable weather in PvP.
- **Normalization sets:** Ensure \\\( \max \text{SP} \\\) and \\\( \max \text{MP} \\\) are computed **within the league/meta** you care about.
- **Purified handling:** Treat *Return* as an additional charge move option where applicable. No stat bonus for purified.
- **Constants calibration:** Tune \\\( \alpha, \beta, \kappa, \lambda, \phi, \gamma, \eta, \theta, \mu \\\) using benchmark species so rankings align with intuition/sim outputs.
- **Breakpoints:** Use the same damage function to test for +1 damage step against representative \\\( D_{\text{def}} \\\) values (per league cluster or boss list). Reward modestly to avoid overfitting.

---

## 10) Minimal Integration Plan

1. Implement the **base** framework (Sections 1–5).  
2. Add **toggles** from Section 6 with defaults in Section 7.  
3. Calibrate constants on a small validation set (e.g., compare to community rankings).  
4. Expose weights/toggles in config so users can favor DPS vs TDO (PvE) or bulk vs pressure (PvP).

---

## 11) Output

For each Pokémon (and moveset), output:  
- PvE: `DPS`, `TDO`, `V_PvE` (and weighted if enabled).  
- PvP: `SP`, `SP_norm`, `MP`, `MP_norm`, `V_PvP` (+ role variants if enabled).  
- Optional: modifiers applied (breakpoint bonus, CMP bonus, coverage, availability penalty).

---

*End of document.*
