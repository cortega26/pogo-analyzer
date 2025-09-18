# Pokémon GO Value Calculation Framework (Enhanced, Implementable)

**Status:** Production‑ready reference (with engine constraints & edge cases)  
**Scope:** End‑to‑end scoring for **PvE** (raids/gyms) and **PvP** (leagues), including optional fine‑tuning toggles (baiting, breakpoints, CMP, coverage, anti‑meta, dodge, relobby).  
**Design goals:** Drop‑in implementable, simulator‑light, and aligned with in‑game mechanics (rounding, caps, multipliers).

---

## 0) Preliminaries & Notation

- **Base stats:** \( (A_{\text{base}}, D_{\text{base}}, S_{\text{base}}) \)
- **IVs:** \( (\text{iv}_A, \text{iv}_D, \text{iv}_S) \)
- **Shadow flag:** \( \text{sh} \in \{0,1\} \)
- **Purified flag:** \( \text{pu} \in \{0,1\} \) *(affects move availability only; no stat multiplier)*
- **Best Buddy flag:** \( \text{bb} \in \{0,1\} \)
- **Combat Power Multiplier (CPM):** \( c(L) \) for \( L \in \{1, 1.5, \dots, 50\} \)  
  *Best Buddy* grants an **effective +1 level CPM lookup** (bounded to CPM table max).

**Shadow multipliers** (apply **pre‑CPM**):
- \( m_A^{\text{sh}} = 1.2^{\text{sh}} \)
- \( m_D^{\text{sh}} = (5/6)^{\text{sh}} \approx 0.833333^{\text{sh}} \)

**Pre‑CPM stats:**
- \( A_0 = (A_{\text{base}} + \text{iv}_A)\cdot m_A^{\text{sh}} \)
- \( D_0 = (D_{\text{base}} + \text{iv}_D)\cdot m_D^{\text{sh}} \)
- \( S_0 = (S_{\text{base}} + \text{iv}_S) \)

> **Purified note**: Purified has no stat multiplier. Its effect is **moveset availability** (e.g., *Return*, *Frustration* windows). Handle this during moveset enumeration.

**Type effectiveness (per type-layer)**: multiply by \( m_{\text{type}} \in \{0.625,\,1.0,\,1.6\} \) **for each effectiveness layer**.  
Examples: double‑weak \(= 1.6^2=2.56\); double‑resist \(= 0.625^2\approx 0.390625\).

**STAB:** \( m_{\text{stab}} = 1.2 \) if move type matches **either** of user’s types (does not stack).  
**Weather (PvE only):** \( m_{\text{weather}} = 1.2 \) if boosted; else 1.0.

---

## 1) Level Inference from Displayed CP/HP

**In‑game CP clamp:**  
\[
\text{CP}(L,\text{bb}) = \max\!\left(10,\ \left\lfloor
\frac{A_0\cdot \sqrt{D_0}\cdot \sqrt{S_0}\cdot \big(c(L^\dagger)\big)^2}{10}
\right\rfloor\right),\ \ \ L^\dagger=\min\!\big(L+\mathbf{1}\{\text{bb}=1\},\ L_{\max,\text{CPM}}\big).
\]

Given observed \( \text{CP}_{\text{obs}} \) (and optionally \( \text{HP}_{\text{obs}} \)), search \( L\in\{1,1.5,\dots,50\} \) and pick the \( L \) such that \( \text{CP}(L,\text{bb})=\text{CP}_{\text{obs}} \). If multiple candidates exist, use

\[
 \text{HP}(L,\text{bb}) = \left\lfloor S_0 \cdot c(L^\dagger) \right\rfloor
\]

to disambiguate. If still tied (rare CPM plateaus), either return **all candidates** or break ties using **known dust/candy costs** if available.

---

## 2) Effective Stats (post level inference)

Let \( L^\* \) be the inferred level and \( c^\* = c(L^\dagger)\) with the same BB bound as above. Then
\[
A = A_0 \cdot c^\*, \quad
D = D_0 \cdot c^\*, \quad
H = \left\lfloor S_0 \cdot c^\* \right\rfloor.
\]

---

## 3) Move Multipliers & Damage

- **STAB**: \( m_{\text{stab}} = 1.2 \) if move type ∈ user types; else 1.0.
- **Weather (PvE only)**: \( m_{\text{weather}} = 1.2 \) if boosted; else 1.0.
- **Type effectiveness**: multiply per layer (see prelims).

**Damage per hit** for a move \( x \in \{\text{fast}, \text{charge}\} \):
\[
\text{Damage}_x = \left\lfloor 0.5 \cdot P_x \cdot \frac{A}{D_{\text{def}}} \cdot
\big(m_{\text{stab}}\cdot m_{\text{weather}} \cdot m_{\text{type}}\big) \right\rfloor + 1.
\]

Use **PvE** or **PvP** move data appropriately:
- PvE: `power_pve`, `duration_s`, `energy_delta_pve` (fast: positive gain; charge: **cost**—store as positive \(E_c\) internally).
- PvP: `power_pvp`, `turns` (each turn = 0.5s), `energy_delta_pvp` (same polarity convention as above in your engine).

**Energy capacity (both modes):** **Cap energy to \([0,100]\)** at all times. Energy overflow is **lost**. Apply cap after every tick/hit and after energy‑from‑damage (PvE).

---

## 4) PvE Value

### 4.1 DPS (rotation-based, energy-constrained, feasible in time)

Let the fast move have duration \( t_f \) (s) and energy gain \( e_f>0 \). Each charge \( c \) has duration \( t_c \) and **cost** \( E_c>0 \). We want the **feasible** rotation (respects time, durations, and energy cap) with highest average DPS over a cycle/window \(W\):
\[
\text{DPS}=\max_{\text{feasible rotation over }W}\;
\frac{\sum \text{Damage}_\text{hits}}{\sum \text{time}_\text{hits}}
\ \ \text{s.t.}\ \ 0\le E_t\le 100,\ \ E_{t^-}\!\ge E_c\ \text{when casting charge},\ \text{cooldowns respected}.
\]

**Energy from damage (optional):** In PvE, grant energy from **damage taken** by the attacker (never from damage dealt):  
\(E_{\text{taken}} \gets E_{\text{taken}} + \rho_E \cdot \Delta \text{HP}_{\text{lost}}\), then re‑cap to \([0,100]\). Default \( \rho_E = 0.5 \) (≈1 energy per 2 HP lost).

### 4.2 Durability & Output
- Prefer **exact** incoming DPS when boss kit is known: compute \( \text{DPS}_{\text{in}} \) from boss moves (using the same damage function, boss A vs your D, with type & weather).
- **Time to Faint:** \( \text{TTF} = H / \text{DPS}_{\text{in}} \).
- **Total Damage Output:** \( \text{TDO} = \text{DPS}\cdot \text{TTF} \).

*(If boss kit unknown, you may use an EHP proxy \( \text{EHP}\approx H\cdot(D/D_{\text{tar}})\) and then \( \text{TTF}=\text{EHP}/\text{DPS}_{\text{in}}\), but be explicit about the calibration \(D_{\text{tar}}\).)*

**Relobby / swap downtime (optional):** Apply \(\text{RelobbyPenalty} = \exp(-\phi \cdot \text{TDO})\) or subtract a fixed downtime per faint to reduce effective DPS/TDO when fainting often.

### 4.3 Raid-party modifiers (optional, off by default)
Multipliers sometimes used by raid calculators; keep off unless simulating a concrete lobby:
- **Friendship damage bonus** \(m_{\text{ally}}\).
- **Mega/Primal aura** \(m_{\text{mega}}\) for matching types (to allies and/or self).  
Apply multiplicatively to outgoing damage terms when enabled.

### 4.4 PvE Score
\[
V_{\text{PvE}} = \text{DPS}^{\alpha}\cdot \text{TDO}^{1-\alpha}, \quad \alpha \in [0.5,\,0.66].
\]
**Boss weighting (optional):** For clusters \( j \) with weights \( w_j \), compute \( V_{\text{PvE,weighted}} = \sum_j w_j \cdot V_{\text{PvE}}^{(j)} \).

---

## 5) PvP Value

### 5.1 Stat Product (Bulk)
\[
\text{SP} = A\cdot D\cdot H, \qquad \text{SP}_{\text{norm}} = \frac{\text{SP}}{\max(\text{SP}\ \text{over reference set in league})}.
\]
Use a **league-specific** reference set (eligible species/forms and CP caps).

### 5.2 Move Pressure (Offense & Shield Dynamics)

**Fast Move Pressure (FMP):** with PvP turns \(u_f\) (each 0.5s) and energy \(e_f\):
\[
\text{FMP} = \frac{\text{Damage}_f}{0.5\cdot u_f} \;+\; \kappa \cdot \frac{e_f}{0.5\cdot u_f},
\]
with \(\kappa\ge 0\) to value EPT vs DPT tradeoffs.

**Charge Move Pressure (CPP):**
- For each charge move \( c \), define a **use rate** \( r_c \) (expected casts per time window or per 100 fast‑generated energy), and **buff EV**:
\[
\text{BuffEV}_c = \sum_k \Delta\text{stage}_k \cdot \Pr_k, \quad
\text{CPP}_c = r_c \cdot \big(\text{Damage}_c + \lambda \cdot \text{BuffEV}_c\big).
\]
(Stages are multiplicative in GO; this EV is a **heuristic** proxy.)
- If two charge moves \( (c_{\text{low}},c_{\text{high}}) \) exist, incorporate **baiting**:
\[
\text{CPP}_{\text{pair}} = p_{\text{bait}}\cdot \text{CPP}_{\text{high}} + (1-p_{\text{bait}})\cdot \text{CPP}_{\text{low}}.
\]

**Move Pressure aggregate (meta‑normalized):**
\[
\text{MP} = \text{FMP} + \max\!\big(\max_c \text{CPP}_c,\, \text{CPP}_{\text{pair}}\big).
\]
Normalize within the league/meta:
- *Simple max scaling:* \( \text{MP}_{\text{norm}} = \text{MP}/\max(\text{MP}\ \text{in meta}) \).
- *Robust (recommended):* \( \text{MP}_{\text{norm}} = \mathrm{clip}_{[0,1]}\big(\frac{\text{MP} - P50}{P95-P50}\big) \) using the meta’s P50/P95.

**Shield-scenario blend (optional):** Compute \( \text{MP}_{0s}, \text{MP}_{1s}, \text{MP}_{2s} \) under different \( p_{\text{bait}} \) and \( r_c \), then
\[
\text{MP}_{\text{blend}} = \omega_0 \text{MP}_{0s} + \omega_1 \text{MP}_{1s} + \omega_2 \text{MP}_{2s},\ \ \sum\omega_i=1,
\]
and use \( \text{MP}_{\text{blend}} \) in place of \( \text{MP} \).

**CMP / initiative rule:** If both sides attempt charge on the same turn, **current Attack (after stage changes)** acts first; exact ties are random. A small CMP bonus can reflect this.

### 5.3 PvP Score
\[
V_{\text{PvP}} = (\text{SP}_{\text{norm}})^{\beta}\cdot (\text{MP}_{\text{norm}})^{1-\beta},
\qquad \beta \in [0.5,\,0.55].
\]

---

## 6) Fine‑Tuning Add‑Ons (Optional Modifiers)

Apply as multiplicative factors to the base scores unless otherwise noted.

### 6.1 Breakpoint Awareness (PvE & PvP)
Evaluate fast/charge damage vs representative \( D_{\text{def}} \) (or common targets). Reward hitting breakpoints:
\[
\text{BP}_{\text{bonus}} = \gamma \cdot \#\{\text{breakpoints hit}\},
\quad V \leftarrow V\cdot (1+\text{BP}_{\text{bonus}}).
\]
*Compute using the same damage function and floor placement (pre‑+1, then +1), with exact type/weather/defense contexts.*

### 6.2 CMP / Initiative Bonus (PvP)
If ties occur, higher current Attack acts first. Give a small bonus for high‑Attack percentiles in league:
\[
\text{CMP}_{\text{bonus}}=\eta \cdot \mathbf{1}\{A \ge \text{percentile}_p(A\,|\,\text{league})\},
\quad V_{\text{PvP}} \leftarrow V_{\text{PvP}}\cdot (1+\text{CMP}_{\text{bonus}}).
\]

### 6.3 Coverage / Typing Score (Both)
Estimate frequency of neutral or SE hits over a **target set** \( \mathcal{T} \). For each target, use the **best** of (fast + either charge) for that matchup.
\[
\text{Coverage}=\frac{\#\{\text{neutral or SE over }\mathcal{T}\}}{|\mathcal{T}|},
\quad V \leftarrow V\cdot \big(1+\theta\cdot(\text{Coverage}-0.5)\big).
\]

### 6.4 Moveset Availability Penalty (Both)
Penalize hard‑to‑access moves (legacy/elite TM/event‑only):
\[
V \leftarrow V\cdot (1-\delta_{\text{availability}}),\ \ \delta_{\text{availability}}\in[0,\,0.1].
\]

### 6.5 PvE Dodge / Downtime (PvE)
- **Incoming:** reduce \( \text{DPS}_{\text{in}} \) during charged windows by factor \( \rho_{\text{dodge}} \).
- **Outgoing:** subtract missed fast cycles and energy gain while dodging.
- **Relobby tax:** apply \( \exp(-\phi\cdot \text{TDO}) \) or simulate fixed downtime per faint.

### 6.6 PvP Role Fit (PvP)
Compute \( V_{\text{lead}}, V_{\text{swap}}, V_{\text{closer}} \) with different weights:
- **Lead:** favor fast DPT and shield pressure (early shields up).
- **Safe‑swap:** favor neutrality and spam.
- **Closer:** favor DPE and nukes (shields down).  
Return all three or \( V_{\text{role}} = \max \).

### 6.7 Anti‑Meta Bonus (PvP)
Given a top‑N meta set \( \mathcal{M} \),
\[
\text{AntiMeta} = \frac{\#\{\text{favored matchups vs }\mathcal{M}\}}{|\mathcal{M}|},\quad
V_{\text{PvP}} \leftarrow V_{\text{PvP}}\cdot (1+\mu\cdot \text{AntiMeta}).
\]

---

## 7) Defaults & Tunables (JSON‑like)

```json
{
  "shared": {
    "gamma_breakpoint": 0.03,
    "eta_cmp": 0.02,
    "theta_coverage": 0.05,
    "availability_penalty": {
      "standard": 0.00, "legacy": 0.02, "elite_tm": 0.04, "event_only": 0.03
    }
  },
  "pve": {
    "alpha": 0.60,
    "enable_energy_from_damage": true,
    "rho_energy_from_damage": 0.5,
    "relobby_phi": 0.08,
    "dodge": { "enabled": false, "rho_dodge": 0.4 },
    "boss_weights": {
      "dragon": 0.25, "flying": 0.20, "double_rock_weak": 0.10, "other": 0.45
    },
    "party_bonuses": {
      "enabled": false,
      "friendship_multiplier": 1.0,
      "mega_aura_multiplier": 1.0
    }
  },
  "pvp": {
    "beta": 0.52,
    "kappa_fast_energy_weight": 1.0,
    "lambda_buff": 0.6,
    "shield_weights": [0.2, 0.5, 0.3],
    "bait": { "a": 0.4, "b": -0.1, "c": 0.35, "d": 0.0 },
    "mu_anti_meta": 0.08,
    "cmp_attack_percentile": 0.7,
    "mp_normalization": "robust"    // values: "max" | "robust"
  }
}
```

---

## 8) Pseudocode (End‑to‑End, Updated)

**Inputs:** base stats, IVs, flags (shadow, purified, best buddy), observed CP/HP (optional), CPM table, move data (PvE & PvP), type chart, weather (PvE), league/meta sets.

### 8.1 Level inference & stats

```pseudo
function infer_level(baseA, baseD, baseS, ivA, ivD, ivS, CP_obs, HP_obs?, isShadow, isBB, CPM):
    A0 = (baseA + ivA) * (1.2 if isShadow else 1.0)
    D0 = (baseD + ivD) * ((5/6) if isShadow else 1.0)
    S0 = (baseS + ivS)

    Lmax = max_key(CPM)
    candidates = []
    for L in [1, 1.5, ..., 50]:
        Lbb = min(L + (1 if isBB else 0), Lmax)
        c_eff = CPM[Lbb]
        CP_calc = max(10, floor(A0 * sqrt(D0) * sqrt(S0) * c_eff^2 / 10))
        if CP_calc == CP_obs:
            if HP_obs is None:
                candidates.append((L, c_eff))
            else:
                HP_calc = floor(S0 * c_eff)
                if HP_calc == HP_obs:
                    candidates.append((L, c_eff))

    if candidates not empty: return best_candidate(candidates)  // policy: first or all
    // fallback to nearest CP; prefer lower L if tie
    bestL = argmin_L |max(10, floor(A0 * sqrt(D0) * sqrt(S0) * CPM[min(L+(1 if isBB else 0), Lmax)]^2 / 10)) - CP_obs|
    Lbb = min(bestL + (1 if isBB else 0), Lmax)
    return (bestL, CPM[Lbb])

function effective_stats(A0, D0, S0, c_eff):
    A = A0 * c_eff
    D = D0 * c_eff
    H = floor(S0 * c_eff)
    return (A, D, H)
```

### 8.2 Damage helpers (context‑aware)

```pseudo
function damage_per_hit(P, A_att, D_def, m_stab, m_weather, m_type):
    return floor(0.5 * P * (A_att / D_def) * (m_stab * m_weather * m_type)) + 1
```

### 8.3 PvE rotation (feasible DP; energy‑from‑damage; relobby/dodge toggles)

```pseudo
function pve_score(attacker, boss, config):
    // Precompute per-move damages with PvE stats and multipliers
    dmg_fast = damage_per_hit(P_fast_pve, A, D_boss, m_stab_f, m_weather, m_type_f)
    for c in charges:
        dmg_chg[c] = damage_per_hit(P_c_pve, A, D_boss, m_stab_c, m_weather, m_type_c)

    // DP over a finite window W (e.g., LCM of move durations or 30s); tick = gcd of durations
    best_dmg_at_state = dict()  // key=(t_mod, energy, cooldown_mod...) -> max dmg
    init_state = (t=0, E=0, dmg=0, cd=ready)
    frontier = {init_state}

    while frontier not empty:
        s = pop(frontier)
        // Option 1: cast fast if available
        if fast_ready(s):
            E2 = min(100, s.E + e_f)
            t2 = s.t + t_f
            dmg2 = s.dmg + dmg_fast
            push_state(t2, E2, dmg2, next_cd_after_fast)
        // Option 2: cast each charge c if energy >= E_c and available
        for c in charges:
            if s.E >= E_c[c] and charge_ready(c, s):
                E2 = s.E - E_c[c]
                t2 = s.t + t_c[c]
                dmg2 = s.dmg + dmg_chg[c]
                push_state(t2, E2, dmg2, next_cd_after_charge(c))
        // Energy from damage (optional): apply after incoming damage tick
        if config.enable_energy_from_damage:
            dHP = incoming_damage_tick(boss, attacker, t_step)   // use boss moves & type/weather
            E2 = min(100, s.E + config.rho_energy_from_damage * dHP_lost)
            // update state with re-capped energy

    best_dps = max_over_states( state.dmg / max(state.t, epsilon) )

    // Durability & TDO
    DPS_in = compute_dps_in(boss, attacker, config.dodge)  // same damage function; apply dodge modifiers
    TTF    = H / max(DPS_in, epsilon)
    TDO    = best_dps * TTF

    // Optional relobby/dodge penalties
    if config.relobby.enabled:
        TDO *= exp(-config.relobby_phi * TDO)

    // Apply optional party multipliers to outgoing damage if enabled
    if config.party_bonuses.enabled:
        best_dps *= (config.party_bonuses.friendship_multiplier * config.party_bonuses.mega_aura_multiplier)
        TDO     *= (config.party_bonuses.friendship_multiplier * config.party_bonuses.mega_aura_multiplier)

    // Final PvE score
    V = best_dps^config.alpha * TDO^(1 - config.alpha)
    return { "DPS": best_dps, "TTF": TTF, "TDO": TDO, "V_PvE": V }
```

### 8.4 PvP pressure & score (with shield/bait blending)

```pseudo
function pvp_score(attacker, league_meta, config):
    // Bulk
    SP = A * D * H
    max_SP = max_SP_in_league(league_meta.ref_set)
    SP_norm = SP / max_SP

    // Fast move pressure
    FMP = (dmg_fast / (0.5 * u_f)) + config.kappa_fast_energy_weight * (e_f / (0.5 * u_f))

    // Charge move pressure
    CPP_scenarios = []
    scenarios = shields_scenarios()  // e.g., 0s,1s,2s with weights w_i
    for sc in scenarios:
        r = estimate_use_rates(attacker, sc)  // e.g., per 100 fast-energy or per time
        p_bait = sigmoid(config.bait.a*EPT + config.bait.b*DPT + config.bait.c*sc.shields + config.bait.d)
        cpp_list = []
        for c in charges:
            BuffEV_c = sum(delta_stage_k * prob_k for effects of c)  // heuristic
            cpp_list.append( r[c] * (dmg_c + config.lambda_buff * BuffEV_c) )
        CPP_pair = max(cpp_list)  // default if single charge
        if has_two_charges:
            // low/high determined by energy cost or typical roles
            CPP_pair = p_bait * cpp_high + (1 - p_bait) * cpp_low
        MP = FMP + max(max(cpp_list), CPP_pair)
        CPP_scenarios.append( (MP, sc.weight) )

    // Meta normalization
    if config.mp_normalization == "robust":
        P50, P95 = meta_MP_percentiles(league_meta, 0.50, 0.95)
        normalize = lambda x: clip((x - P50) / max(P95 - P50, eps), 0, 1)
    else:
        MP_max = meta_MP_max(league_meta)
        normalize = lambda x: x / max(MP_max, eps)

    MP_blend = sum( normalize(MP) * w for (MP,w) in CPP_scenarios )

    V = (SP_norm^config.beta) * (MP_blend^(1 - config.beta))

    // Optional post-modifiers
    if config.cmp_attack_percentile is not None:
        if A >= percentile_in_league(A, config.cmp_attack_percentile):
            V *= (1 + config.eta_cmp)

    if config.coverage_enabled:
        cov = coverage_score(attacker, league_meta.targets)  // best-of (fast + one charge) per target
        V *= (1 + config.theta_coverage * (cov - 0.5))

    if config.anti_meta_enabled:
        am = anti_meta_rate(attacker, league_meta.topN)
        V *= (1 + config.mu_anti_meta * am)

    return {
      "SP": SP, "SP_norm": SP_norm,
      "MP": MP_blend, "MP_norm": MP_blend,  // already normalized
      "V_PvP": V
    }
```

---

## 9) Implementation Notes & Guardrails

- **Data separation:** Always use PvE move stats for PvE and PvP move stats for PvP. Disable weather in PvP.
- **Energy sign convention:** Store **charge costs as positive \(E_c\)** internally; apply sign only at ingestion boundaries.
- **Normalization sets:** Ensure \(\max \text{SP}\) and \(\max \text{MP}\) (or P50/P95) are computed **within the league/meta** in scope.
- **Best Buddy bounds:** Don’t index past CPM table ceiling. If league CP caps are enforced, BB can make a Pokémon exceed the cap—this is intended and should be reflected in eligibility logic.
- **Breakpoints:** Use the same damage function and rounding (floor then +1). Recalculate under each scenario (type/weather/buffs).
- **Dodge model:** When enabled, **both** incoming (reduce \(\text{DPS}_{\text{in}}\)) **and** outgoing (lost fast cycles/energy) must be applied, or you’ll overstate DPS and TTF simultaneously.
- **Type layers:** For dual‑type targets, apply type multipliers **per layer**; for dual‑type users, STAB is single 1.2 if move matches either type (no stacking).
- **Minimum damage:** The `+1` already guarantees \(\ge 1\); don’t add another clamp.
- **Charge priority:** If you later do turn‑accurate PvP, model fast‑move denial correctly when both sides throw on the same turn.

---

## 10) Minimal Integration Plan

1. Implement the **base** framework (Secs. 1–5), including CP clamp and energy caps.
2. Add **toggles** from Sec. 6 with defaults in Sec. 7.
3. Calibrate constants (\(\alpha, \beta, \kappa, \lambda, \phi, \gamma, \eta, \theta, \mu\)) against a small validation set (compare to community rankings/sim results).
4. Expose weights/toggles in config so users can favor DPS vs. TDO (PvE) or bulk vs. pressure (PvP).
5. Add optional raid‑party modifiers (friendship/mega) if you plan to report realistic multi‑trainer raid DPS/TDO.

---

## 11) Output Contract

For each Pokémon (and moveset), output:  
- **PvE:** `DPS`, `TTF`, `TDO`, `V_PvE` (and weighted if enabled).  
- **PvP:** `SP`, `SP_norm`, `MP`, `MP_norm` (if robust, MP\_norm = normalized MP), `V_PvP` (+ role variants if enabled).  
- **Optional:** modifiers applied (breakpoint bonus count, CMP bonus, coverage delta, availability penalty), plus configuration snapshot.

---

## 12) QA Checklist & Test Vectors

1. **CP clamp:** Level 1, 0/0/0 baby species → reported CP **≥ 10**.  
2. **Energy cap:** Spammy fast into 35E charge; ensure energy **never exceeds 100** and overflow is lost.  
3. **Breakpoint harness:** Lower \(D_{\text{def}}\) by 1 around a suspected breakpoint; confirm +1 occurs **only** when pre‑+1 floor crosses.  
4. **CMP:** Two identical mons; one at +1 Atk stage takes charge priority.  
5. **Dodge toggle:** Enabling dodge decreases **outgoing DPS** (lost fasts) while increasing **TTF**.  
6. **Best Buddy bounds:** At CPM table max, no out‑of‑range index; BB still uses last CPM.  
7. **Double effectiveness:** Ensure per‑layer multiplication (e.g., 2.56 and ~0.390625 appear in cases with double weaknesses/resists).

---

## 13) “AI Prompt Style” Implementation Instructions (paste into your task runner)

> **Goal:** Implement the Pokémon GO Value Calculation Framework with exact rounding, energy caps, and meta‑normalized PvP pressure.  
> **Key rules:** CP clamp to 10, energy ∈ [0,100], per‑layer type multipliers, floor‑then‑plus‑1 damage, PvP turns = 0.5s, PvE weather allowed, PvP weather off.

- **Data ingestion**
  - Load base stats, IVs, shadow/purified/BB flags, CPM table.
  - Load PvE/PvP move data separately. Convert charge energy to **positive costs \(E_c\)** internally.
  - Load type chart and weather mapping (PvE).
  - Load league/meta rosters; precompute reference **SP max** and MP quantiles (P50/P95) per league when using robust normalization.

- **Core math**
  - Pre‑CPM shadow multipliers: A×1.2, D×(5/6).
  - CP formula with **max(10, …)** and BB CPM lookup bounded to CPM max level.
  - Effective stats: \(A=A_0 c\), \(D=D_0 c\), \(H=\lfloor S_0 c\rfloor\).

- **Damage function**
  - \( \text{Damage} = \lfloor 0.5\cdot P \cdot (A/D_{\text{def}})\cdot m_{\text{stab}} m_{\text{weather}} m_{\text{type}} \rfloor + 1\).
  - Apply type multipliers per layer; STAB if matches either user type; weather only in PvE.
  - Respect energy cap \([0,100]\) after each gain/cost and after energy‑from‑damage (if enabled).

- **PvE**
  - Compute feasible rotation (DP/DFS over a finite window, or periodic cycle); no illegal cast before energy \(E_c\) and respect durations.
  - Incoming DPS from boss kit using same damage function; apply dodge toggles to both incoming and outgoing appropriately.
  - \( \text{TTF}=H/\text{DPS}_{\text{in}} \), \( \text{TDO}=\text{DPS}\cdot \text{TTF} \); optional relobby penalty and party multipliers.
  - Score: \(V_{\text{PvE}} = \text{DPS}^{\alpha}\cdot \text{TDO}^{1-\alpha}\).

- **PvP**
  - Bulk: SP and league‑normalized SP.
  - Pressure: FMP + CPP (with bait pair where applicable); estimate \(r_c\) (per time or per 100 fast energy).
  - Normalize MP via **robust** (P50/P95) or max, per config. Blend across shield scenarios by weights.
  - Final \(V_{\text{PvP}}\) with optional CMP/coverage/anti‑meta multipliers.

- **Outputs**
  - Emit PvE and PvP metrics plus config snapshot and applied modifiers. Add unit tests for the QA checklist items.

---

*End of document.*
