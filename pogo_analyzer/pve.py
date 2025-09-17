"""PvE rotation search and value scoring helpers."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from itertools import permutations, product
from typing import Iterable, Sequence

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
            energy = min(energy + fast_move.energy_gain, _ENERGY_CAP)
            total_damage += fast_damage
            total_time += fast_move.duration
            fast_moves_used += 1
            if math.isclose(energy, _ENERGY_CAP) and move.energy_cost > _ENERGY_CAP - _ENERGY_EPS:
                # Reached cap; if the cost still cannot be met we would loop forever.
                break

        if energy + _ENERGY_EPS < move.energy_cost:
            raise RuntimeError("Rotation simulation failed to gather enough energy for a charge move.")

        energy -= move.energy_cost
        total_damage += damage
        total_time += move.duration
        usage[move.name] += 1

    return _SimulationResult(total_damage, total_time, fast_moves_used, usage, energy)


def _evaluate_candidate(
    fast_move: FastMove,
    simulation: _SimulationResult,
    attacker_attack: float,
    defender_defense: float,
) -> _RotationCandidate | None:
    if simulation.fast_moves_used == 0 and simulation.charge_usage:
        # Should not happen because each charge requires at least one fast move.
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
) -> float:
    """Compute the best-possible rotation DPS for the provided move set."""

    best_candidate = _best_rotation(
        fast_move,
        charge_moves,
        attacker_attack,
        defender_defense,
        max_total_charge_uses=max_total_charge_uses,
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
    max_total_charge_uses: int = _MAX_TOTAL_CHARGE_USES,
) -> dict[str, float | Counter[str]]:
    """Compute full PvE score outputs for a Pokémon."""

    if attacker_attack <= 0 or attacker_defense <= 0:
        raise ValueError("Attacker stats must be positive.")
    if incoming_dps <= 0:
        raise ValueError("incoming_dps must be positive.")

    best_candidate = _best_rotation(
        fast_move,
        charge_moves,
        attacker_attack,
        target_defense,
        max_total_charge_uses=max_total_charge_uses,
    )
    dps = best_candidate.dps
    ehp = estimate_ehp(attacker_defense, attacker_hp, target_defense=target_defense)
    time_to_faint = ehp / incoming_dps
    tdo = dps * time_to_faint
    value = pve_value(dps, tdo, alpha=alpha)

    return {
        "dps": dps,
        "cycle_damage": best_candidate.total_damage,
        "cycle_time": best_candidate.total_time,
        "fast_moves_per_cycle": best_candidate.fast_moves,
        "charge_usage_per_cycle": best_candidate.charge_usage,
        "ehp": ehp,
        "tdo": tdo,
        "value": value,
        "alpha": alpha,
    }


__all__ = [
    "FastMove",
    "ChargeMove",
    "rotation_dps",
    "estimate_ehp",
    "pve_value",
    "compute_pve_score",
]
