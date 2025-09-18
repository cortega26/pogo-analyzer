"""PvE rotation search and value scoring helpers."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from itertools import permutations, product
from typing import Iterable, Mapping, Sequence

from .formulas import damage_per_hit

_ENERGY_CAP = 100.0
_MAX_TOTAL_CHARGE_USES = 6
_ENERGY_EPS = 1e-6


@dataclass(frozen=True)
class FastMove:
    """Container describing a PvE fast move."""

    name: str
    power: float
    energy_gain: float
    duration: float
    stab: bool = False
    weather_boosted: bool = False
    type_effectiveness: float = 1.0

    def __post_init__(self) -> None:  # noqa: D401 - succinct validation.
        if self.power < 0:
            raise ValueError("Fast move power cannot be negative.")
        if self.energy_gain <= 0:
            raise ValueError("Fast move energy gain must be positive.")
        if self.duration <= 0:
            raise ValueError("Fast move duration must be positive.")
        if self.type_effectiveness <= 0:
            raise ValueError("Type effectiveness must be positive.")


@dataclass(frozen=True)
class ChargeMove:
    """Container describing a PvE charge move."""

    name: str
    power: float
    energy_cost: float
    duration: float
    stab: bool = False
    weather_boosted: bool = False
    type_effectiveness: float = 1.0
    availability: str | None = None  # optional tag for legacy/event availability tweaks

    def __post_init__(self) -> None:  # noqa: D401 - succinct validation.
        if self.power < 0:
            raise ValueError("Charge move power cannot be negative.")
        if self.energy_cost <= 0:
            raise ValueError("Charge move energy cost must be positive.")
        if self.energy_cost > _ENERGY_CAP:
            raise ValueError("Charge move energy cost exceeds PvE energy cap.")
        if self.duration <= 0:
            raise ValueError("Charge move duration must be positive.")
        if self.type_effectiveness <= 0:
            raise ValueError("Type effectiveness must be positive.")


@dataclass(frozen=True)
class _SimulationResult:
    total_damage: float
    total_time: float
    fast_moves_used: int
    charge_usage: Counter[str]
    ending_energy: float


@dataclass(frozen=True)
class _RotationCandidate:
    dps: float
    total_damage: float
    total_time: float
    fast_moves: float
    charge_usage: Counter[str]


def _unique_permutations(indices: Sequence[int]) -> Iterable[Sequence[int]]:
    """Yield unique permutations of a sequence that may contain duplicates."""

    seen: set[tuple[int, ...]] = set()
    for order in permutations(indices, len(indices)):
        if order not in seen:
            seen.add(order)
            yield order


def _simulate_sequence(
    fast_move: FastMove,
    charge_moves: Sequence[ChargeMove],
    charge_sequence: Sequence[int],
    attacker_attack: float,
    defender_defense: float,
    *,
    energy_per_second_from_damage: float = 0.0,
) -> _SimulationResult:
    fast_damage = damage_per_hit(
        fast_move.power,
        attacker_attack,
        defender_defense,
        stab=fast_move.stab,
        weather_boosted=fast_move.weather_boosted,
        type_effectiveness=fast_move.type_effectiveness,
    )
    charge_damages = [
        damage_per_hit(
            charge.power,
            attacker_attack,
            defender_defense,
            stab=charge.stab,
            weather_boosted=charge.weather_boosted,
            type_effectiveness=charge.type_effectiveness,
        )
        for charge in charge_moves
    ]

    energy = 0.0
    total_damage = 0.0
    total_time = 0.0
    fast_moves_used = 0
    usage: Counter[str] = Counter()

    for index in charge_sequence:
        move = charge_moves[index]
        damage = charge_damages[index]
        while energy + _ENERGY_EPS < move.energy_cost:
            energy = min(
                energy
                + fast_move.energy_gain
                + (fast_move.duration * energy_per_second_from_damage),
                _ENERGY_CAP,
            )
            total_damage += fast_damage
            total_time += fast_move.duration
            fast_moves_used += 1
            if math.isclose(energy, _ENERGY_CAP) and energy + _ENERGY_EPS < move.energy_cost:
                break

        if energy + _ENERGY_EPS < move.energy_cost:
            raise RuntimeError("Rotation simulation failed to gather enough energy for a charge move.")

        energy -= move.energy_cost
        total_damage += damage
        total_time += move.duration
        usage[move.name] += 1
        if energy_per_second_from_damage > 0:
            energy = min(energy + move.duration * energy_per_second_from_damage, _ENERGY_CAP)

    return _SimulationResult(total_damage, total_time, fast_moves_used, usage, energy)


def _evaluate_candidate(
    fast_move: FastMove,
    simulation: _SimulationResult,
    attacker_attack: float,
    defender_defense: float,
) -> _RotationCandidate | None:
    if simulation.fast_moves_used == 0 and simulation.charge_usage:
        return None

    fast_damage = damage_per_hit(
        fast_move.power,
        attacker_attack,
        defender_defense,
        stab=fast_move.stab,
        weather_boosted=fast_move.weather_boosted,
        type_effectiveness=fast_move.type_effectiveness,
    )

    fractional_fast = simulation.ending_energy / fast_move.energy_gain
    effective_fast_moves = simulation.fast_moves_used - fractional_fast
    if effective_fast_moves < 0:
        return None

    effective_time = simulation.total_time - (fast_move.duration * fractional_fast)
    effective_damage = simulation.total_damage - (fast_damage * fractional_fast)

    if effective_time <= 0:
        return None

    dps = effective_damage / effective_time
    return _RotationCandidate(dps, effective_damage, effective_time, effective_fast_moves, simulation.charge_usage)


def _best_rotation(
    fast_move: FastMove,
    charge_moves: Sequence[ChargeMove],
    attacker_attack: float,
    defender_defense: float,
    *,
    max_total_charge_uses: int = _MAX_TOTAL_CHARGE_USES,
    energy_per_second_from_damage: float = 0.0,
    dodge_factor: float | None = None,
) -> _RotationCandidate:
    fast_only_damage = damage_per_hit(
        fast_move.power,
        attacker_attack,
        defender_defense,
        stab=fast_move.stab,
        weather_boosted=fast_move.weather_boosted,
        type_effectiveness=fast_move.type_effectiveness,
    )
    fast_only_dps = fast_only_damage / fast_move.duration
    if dodge_factor is not None:
        fast_only_dps *= max(0.0, 1.0 - dodge_factor)
    best_candidate = _RotationCandidate(
        fast_only_dps,
        fast_only_damage,
        fast_move.duration,
        1.0,
        Counter(),
    )

    if not charge_moves:
        return best_candidate

    for total_charges in range(1, max_total_charge_uses + 1):
        for counts in product(range(total_charges + 1), repeat=len(charge_moves)):
            if sum(counts) != total_charges:
                continue
            indices: list[int] = []
            for index, count in enumerate(counts):
                indices.extend([index] * count)
            if not indices:
                continue
            for sequence in _unique_permutations(indices):
                try:
                    simulation = _simulate_sequence(
                        fast_move,
                        charge_moves,
                        sequence,
                        attacker_attack,
                        defender_defense,
                        energy_per_second_from_damage=energy_per_second_from_damage,
                    )
                except RuntimeError:
                    continue
                candidate = _evaluate_candidate(
                    fast_move,
                    simulation,
                    attacker_attack,
                    defender_defense,
                )
                if candidate is None:
                    continue
                candidate_dps = candidate.dps
                if dodge_factor is not None:
                    candidate_dps *= max(0.0, 1.0 - dodge_factor)
                    candidate = _RotationCandidate(
                        candidate_dps,
                        candidate.total_damage,
                        candidate.total_time,
                        candidate.fast_moves,
                        candidate.charge_usage,
                    )
                if candidate.dps > best_candidate.dps + 1e-9:
                    best_candidate = candidate

    return best_candidate


def rotation_dps(
    fast_move: FastMove,
    charge_moves: Sequence[ChargeMove],
    attacker_attack: float,
    defender_defense: float,
    *,
    max_total_charge_uses: int = _MAX_TOTAL_CHARGE_USES,
    energy_per_second_from_damage: float = 0.0,
    dodge_factor: float | None = None,
) -> float:
    """Compute the best-possible rotation DPS for the provided move set."""

    best_candidate = _best_rotation(
        fast_move,
        charge_moves,
        attacker_attack,
        defender_defense,
        max_total_charge_uses=max_total_charge_uses,
        energy_per_second_from_damage=energy_per_second_from_damage,
        dodge_factor=dodge_factor,
    )
    return best_candidate.dps


def estimate_ehp(defense: float, hp: int, *, target_defense: float) -> float:
    """Approximate effective HP (EHP) for raid simulations."""

    if defense <= 0:
        raise ValueError("Defense must be positive.")
    if hp <= 0:
        raise ValueError("HP must be positive.")
    if target_defense <= 0:
        raise ValueError("Target defense must be positive.")
    return hp * (defense / target_defense)


def pve_value(dps: float, tdo: float, *, alpha: float = 0.6) -> float:
    """Combine DPS and TDO into a single PvE value score."""

    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1 (exclusive).")
    if dps < 0 or tdo < 0:
        raise ValueError("dps and tdo must be non-negative.")
    return (dps**alpha) * (tdo ** (1 - alpha))


def _apply_multipliers(
    value: float,
    *,
    breakpoints_hit: int | None,
    gamma_breakpoint: float,
    coverage: float | None,
    theta_coverage: float,
    availability_penalty: float,
) -> tuple[float, dict[str, float]]:
    modifiers: dict[str, float] = {}
    adjusted = value
    if breakpoints_hit:
        bp_bonus = 1.0 + gamma_breakpoint * breakpoints_hit
        adjusted *= bp_bonus
        modifiers["breakpoint_bonus"] = bp_bonus
    if coverage is not None:
        cov_bonus = 1.0 + theta_coverage * (coverage - 0.5)
        adjusted *= cov_bonus
        modifiers["coverage_bonus"] = cov_bonus
    if availability_penalty > 0:
        penalty = max(0.0, min(availability_penalty, 0.99))
        factor = 1.0 - penalty
        adjusted *= factor
        modifiers["availability_penalty"] = factor
    return adjusted, modifiers


def _compute_single_pve(
    attacker_attack: float,
    attacker_defense: float,
    attacker_hp: int,
    fast_move: FastMove,
    charge_moves: Sequence[ChargeMove],
    *,
    target_defense: float,
    incoming_dps: float,
    alpha: float,
    energy_from_damage_ratio: float,
    relobby_penalty: float | None,
    max_total_charge_uses: int,
    dodge_factor: float | None,
    breakpoints_hit: int | None,
    gamma_breakpoint: float,
    coverage: float | None,
    theta_coverage: float,
    availability_penalty: float,
) -> dict[str, float | Counter[str] | None]:
    if attacker_attack <= 0 or attacker_defense <= 0:
        raise ValueError("Attacker stats must be positive.")
    if incoming_dps <= 0:
        raise ValueError("incoming_dps must be positive.")
    if energy_from_damage_ratio < 0:
        raise ValueError("energy_from_damage_ratio must be non-negative.")
    if dodge_factor is not None and not 0 <= dodge_factor < 1:
        raise ValueError("dodge_factor must lie in [0, 1).")

    energy_per_second = incoming_dps * energy_from_damage_ratio
    best_candidate = _best_rotation(
        fast_move,
        charge_moves,
        attacker_attack,
        target_defense,
        max_total_charge_uses=max_total_charge_uses,
        energy_per_second_from_damage=energy_per_second,
        dodge_factor=dodge_factor,
    )

    dps = best_candidate.dps
    ehp = estimate_ehp(attacker_defense, attacker_hp, target_defense=target_defense)
    effective_incoming_dps = incoming_dps * (1.0 - dodge_factor) if dodge_factor else incoming_dps
    time_to_faint = ehp / effective_incoming_dps
    tdo = dps * time_to_faint
    value_raw = pve_value(dps, tdo, alpha=alpha)
    penalty_factor = 1.0
    if relobby_penalty is not None and relobby_penalty > 0:
        penalty_factor = math.exp(-relobby_penalty * tdo)
    value_base = value_raw * penalty_factor

    adjusted_value, modifiers = _apply_multipliers(
        value_base,
        breakpoints_hit=breakpoints_hit,
        gamma_breakpoint=gamma_breakpoint,
        coverage=coverage,
        theta_coverage=theta_coverage,
        availability_penalty=availability_penalty,
    )

    return {
        "dps": dps,
        "cycle_damage": best_candidate.total_damage,
        "cycle_time": best_candidate.total_time,
        "fast_moves_per_cycle": best_candidate.fast_moves,
        "charge_usage_per_cycle": best_candidate.charge_usage,
        "ehp": ehp,
        "tdo": tdo,
        "value": adjusted_value,
        "value_raw": value_raw,
        "alpha": alpha,
        "energy_from_damage_ratio": energy_from_damage_ratio,
        "relobby_penalty": relobby_penalty,
        "penalty_factor": penalty_factor,
        "dodge_factor": dodge_factor,
        "modifiers": modifiers,
    }


def compute_pve_score(
    attacker_attack: float,
    attacker_defense: float,
    attacker_hp: int,
    fast_move: FastMove,
    charge_moves: Sequence[ChargeMove],
    *,
    target_defense: float,
    incoming_dps: float,
    alpha: float = 0.6,
    energy_from_damage_ratio: float = 0.0,
    relobby_penalty: float | None = None,
    scenarios: Sequence[Mapping[str, float]] | None = None,
    max_total_charge_uses: int = _MAX_TOTAL_CHARGE_USES,
    dodge_factor: float | None = None,
    breakpoints_hit: int | None = None,
    gamma_breakpoint: float = 0.0,
    coverage: float | None = None,
    theta_coverage: float = 0.0,
    availability_penalty: float = 0.0,
) -> dict[str, float | Counter[str] | None]:
    """Compute full PvE score outputs for a Pokémon."""

    if scenarios:
        scenario_results: list[dict[str, float | Counter[str] | None]] = []
        total_weight = 0.0
        weighted_value = 0.0
        for scenario in scenarios:
            weight = float(scenario.get("weight", 1.0))
            scenario_result = _compute_single_pve(
                attacker_attack,
                attacker_defense,
                attacker_hp,
                fast_move,
                charge_moves,
                target_defense=float(scenario.get("target_defense", target_defense)),
                incoming_dps=float(scenario.get("incoming_dps", incoming_dps)),
                alpha=alpha,
                energy_from_damage_ratio=float(
                    scenario.get("energy_from_damage_ratio", energy_from_damage_ratio)
                ),
                relobby_penalty=scenario.get("relobby_penalty", relobby_penalty),
                max_total_charge_uses=max_total_charge_uses,
                dodge_factor=scenario.get("dodge_factor", dodge_factor),
                breakpoints_hit=int(scenario.get("breakpoints_hit", breakpoints_hit or 0))
                if scenario.get("breakpoints_hit") is not None
                else breakpoints_hit,
                gamma_breakpoint=float(
                    scenario.get("gamma_breakpoint", gamma_breakpoint)
                ),
                coverage=float(scenario.get("coverage", coverage))
                if scenario.get("coverage") is not None
                else coverage,
                theta_coverage=float(
                    scenario.get("theta_coverage", theta_coverage)
                ),
                availability_penalty=float(
                    scenario.get("availability_penalty", availability_penalty)
                ),
            )
            scenario_result["weight"] = weight
            scenario_results.append(scenario_result)
            total_weight += weight
            weighted_value += weight * float(scenario_result["value"])

        aggregate_value = weighted_value / total_weight if total_weight > 0 else 0.0
        return {
            "value": aggregate_value,
            "alpha": alpha,
            "scenarios": scenario_results,
            "weights_total": total_weight,
        }

    return _compute_single_pve(
        attacker_attack,
        attacker_defense,
        attacker_hp,
        fast_move,
        charge_moves,
        target_defense=target_defense,
        incoming_dps=incoming_dps,
        alpha=alpha,
        energy_from_damage_ratio=energy_from_damage_ratio,
        relobby_penalty=relobby_penalty,
        max_total_charge_uses=max_total_charge_uses,
        dodge_factor=dodge_factor,
        breakpoints_hit=breakpoints_hit,
        gamma_breakpoint=gamma_breakpoint,
        coverage=coverage,
        theta_coverage=theta_coverage,
        availability_penalty=availability_penalty,
    )


__all__ = [
    "FastMove",
    "ChargeMove",
    "rotation_dps",
    "estimate_ehp",
    "pve_value",
    "compute_pve_score",
]
