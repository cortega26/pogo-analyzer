# Pokémon GO Value Calculation Framework

This document defines formulas for inferring Pokémon **level from CP and
IVs** and then using that to compute **PvE** and **PvP** value scores.

------------------------------------------------------------------------

## 0) Preliminaries

-   Base stats: (A_base, D_base, S_base)
-   IVs: (iv_A, iv_D, iv_S)
-   Shadow flag: sh ∈ {0,1}
-   Purified flag: pu ∈ {0,1}
-   Best Buddy flag: bb ∈ {0,1}
-   Combat Power Multiplier (CPM): c(L), defined for L ∈ {1,1.5,...,50}
    (and effective +1 level if Best Buddy active)

Shadow multipliers:

m_A\^sh = 1.2\^sh\
m_D\^sh = 0.83\^sh

Pre-CPM stats:

A0 = (A_base + iv_A) \* m_A\^sh\
D0 = (D_base + iv_D) \* m_D\^sh\
S0 = (S_base + iv_S)

------------------------------------------------------------------------

## 1) Inferring Level from CP

CP formula:

CP(L,bb) = floor( A0 \* sqrt(D0) \* sqrt(S0) \* (c(L + 1{bb=1}))\^2 / 10
)

Given observed CP_obs, search L ∈ {1,1.5,...,50}:\
Pick L such that CP(L,bb) = CP_obs.\
If multiple candidates exist, use observed HP = floor(S0 \* c(L+bb)) to
disambiguate.

------------------------------------------------------------------------

## 2) Effective Stats (once level inferred)

Let c\* = c(L\* + 1{bb=1}) where L\* is the inferred level.

A = A0 \* c\*\
D = D0 \* c\*\
H = floor(S0 \* c\*)

------------------------------------------------------------------------

## 3) Move Multipliers

-   STAB: m_stab = 1.2 if move type matches Pokémon type(s), else 1.0
-   Weather: m_weather = 1.2 if boosted, else 1.0
-   Effectiveness: m_type ∈ {0.625, 1.0, 1.6} (applied twice if double)

Damage formula:

Damage_x = floor(0.5 \* P_x \* (A / D_def) \* (m_stab \* m_weather \*
m_type)) + 1

------------------------------------------------------------------------

## 4) PvE Value

### DPS (rotation-based)

DPS = max\_{n_f,n_c} ( n_f \* Damage_f + Σ n_c \* Damage_c ) / ( n_f \*
t_f + Σ n_c \* t_c ) subject to: n_f \* e_f ≥ Σ n_c \* E_c

### Durability

EHP ≈ H \* D / D_tar\
TTF = EHP / DPS_in\
TDO = DPS \* TTF

### PvE Score

V_PvE = DPS\^α \* TDO\^(1-α), with α ∈ \[0.5,0.66\]

------------------------------------------------------------------------

## 5) PvP Value

### Stat Product

SP = A \* D \* H\
SP_norm = SP / max(SP over reference set)

### Move Pressure

FMP = Damage_f / (u_f*0.5) + κ * (e_f / (u_f*0.5))\
CPP_c = r_c * (Damage_c + λ \* buff_indicator)\
CPP_pair = p_bait \* CPP_high + (1 - p_bait) \* CPP_low\
MP = FMP + max(CPP_c, CPP_pair)\
MP_norm = MP / max(MP in meta)

### PvP Score

V_PvP = (SP_norm)\^β \* (MP_norm)\^(1-β), with β ≈ 0.5--0.55

------------------------------------------------------------------------

## 6) Pseudocode

INPUT: baseA, baseD, baseS, ivA, ivD, ivS, CP_obs, isShadow, isBB

A0 = (baseA + ivA) \* (1.2 if isShadow else 1.0)\
D0 = (baseD + ivD) \* (0.83 if isShadow else 1.0)\
S0 = (baseS + ivS)

for L in levels:\
c_eff = CPM\[L + (1 if isBB else 0)\]\
CP_calc = floor(A0 \* sqrt(D0) \* sqrt(S0) \* c_eff\^2 / 10)\
if CP_calc == CP_obs:\
return L, c_eff

Then compute A, D, H and plug into PvE/PvP formulas.
