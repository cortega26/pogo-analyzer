# CLI quick checks

This guide walks through the single-Pokémon quick-check workflow exposed by `pogo-raid-scoreboard`.
It focuses on the CLI flags that power raid (PvE) and league (PvP) evaluations so you can sanity-check
an individual build without generating the full scoreboard export.

## Flag overview

| Flag | Purpose |
| ---- | ------- |
| `--pokemon-name` | Nickname used for the evaluation. Doubles as the lookup key for dataset guidance. |
| `--combat-power` (`--cp`) | Observed CP used for the raid score baseline and level inference. |
| `--ivs ATT DEF STA` | IV spread (attack, defence, stamina). Required for quick checks. |
| `--shadow` / `--purified` / `--lucky` / `--best-buddy` (`--bb`) | Status toggles that change scoring or inference. |
| `--needs-tm` / `--has-special-move` | Describe whether an exclusive move is already unlocked. |
| `--target-cp` | Desired raid-ready CP. Used to flag underpowered builds. |
| `--base-stats ATK DEF STA` | Species base stats. Required for CP→level inference, PvE, and PvP outputs. |
| `--fast ...` / `--charge ...` | Move descriptors used to evaluate PvE rotations and PvP pressure. |
| `--target-defense` / `--incoming-dps` / `--alpha` | PvE tuning knobs. Provide defence, incoming DPS, and DPS↔TDO blend. |
| `--league-cap` / `--beta` / `--sp-ref` / `--mp-ref` / `--bait-prob` | PvP tuning knobs. Select league and weighting factors. |

### Move descriptor recap

- Fast moves: `name,power,energy_gain,duration[,stab=...][,weather=...][,type=...][,turns=...]`
- Charged moves: `name,power,energy_cost,duration[,stab=...][,weather=...][,type=...][,reliability=...][,buff=...]`

Use `turns` to unlock PvP timing, `stab=true` when the move matches species typing, and `type=`/`effectiveness=` to apply
non-standard multipliers. Passing `--weather` boosts all moves unless explicitly overridden per descriptor.

## PvE quick check

Run the command below to inspect a raid build without enabling the PvE/PvP extra outputs. The CLI prints a priority
recommendation, highlights missing exclusive moves, and surfaces dataset guidance.

```bash
pogo-raid-scoreboard \
  --pokemon-name Hydreigon \
  --combat-power 3200 \
  --ivs 15 14 15 \
  --shadow \
  --needs-tm \
  --notes "Needs Brutal Swing from CD."
```

Expected output:

```
Single Pokémon evaluation
-------------------------
Name: Hydreigon (shadow)
Combat Power: 3200
IVs: 15/14/15
Recommended Charged Move: Brutal Swing
Action: Needs Brutal Swing (Community Day / Elite TM).
Status: Shadow, Exclusive move missing
Raid Score: 89.0/100
Priority Tier: A (High)
Notes: Needs Brutal Swing from CD. Needs Brutal Swing (Community Day / Elite TM). Applied shadow damage bonus to baseline score due to missing dedicated template.
```

## PvE + PvP quick check with level inference

Provide species base stats and move descriptors to unlock the extended PvE and PvP sections. The CLI infers the
underlying level/CPM, prints the effective stats, and reports both value scores. The example below targets a
Great League evaluation (`--league-cap 1500`).

```bash
pogo-raid-scoreboard \
  --pokemon-name Hydreigon \
  --combat-power 3325 \
  --ivs 15 15 15 \
  --base-stats 256 188 216 \
  --fast 'Snarl,12,13,1.0,turns=4,stab=true' \
  --charge 'Brutal Swing,65,40,1.9,stab=true' \
  --target-defense 180 \
  --incoming-dps 35 \
  --alpha 0.6 \
  --league-cap 1500 \
  --beta 0.52
```

Expected output (abridged to the key sections):

```
Single Pokémon evaluation
-------------------------
Name: Hydreigon
Combat Power: 3325
IVs: 15/15/15
Recommended Charged Move: Brutal Swing
Action: Needs Brutal Swing (Community Day / Elite TM).
Raid Score: 86.2/100
Priority Tier: A (High)
Notes: Needs Brutal Swing (Community Day / Elite TM).

Inferred build stats
--------------------
Species: Hydreigon
Level: 33.5
CPM: 0.752729
Effective Attack: 203.99
Effective Defense: 152.80
Effective HP: 173

PvE value
---------
Rotation DPS: 14.61
Cycle Damage: 72.69
Cycle Time: 4.98s
Fast Moves / Cycle: 3.08
Charge Use / Cycle: Brutal Swing: 1.00
EHP: 146.86
TDO: 61.29
PvE Value (alpha=0.60): 25.92

PvP value (Great League)
---------------------------
Stat Product: 5392483.54
Normalised Stat Product: 3.3703
Move Pressure: 9.90
Normalised Move Pressure: 0.2063
PvP Score (beta=0.52): 0.8817
```

### Tips

- Supply additional `--charge` descriptors when a PvP set relies on multiple charged moves; the CLI tracks per-cycle usage.
- Use `--observed-hp` whenever multiple levels share the same CP (common around level 15). The additional data point lets the
  inference step pick the correct level.
- Pass `--weather` to boost all moves simultaneously; override specific moves with `weather=false` or `type=1.6` tokens.
- League presets follow Great (default), Ultra (`--league-cap 2500`), and Master (omit the cap to evaluate unrestricted stats).
