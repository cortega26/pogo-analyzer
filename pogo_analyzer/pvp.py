"""PvP stat product and move pressure scoring utilities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

__all__ = [
    "PvpFastMove",
    "PvpChargeMove",
    "LeagueConfig",
    "DEFAULT_LEAGUE_CONFIGS",
    "stat_product",
    "normalise",
    "fast_move_pressure",
    "charge_move_pressure",
    "pair_charge_pressure",
    "move_pressure",
    "compute_pvp_score",
]


@dataclass(frozen=True)
class PvpFastMove:
    """Container describing a PvP fast move."""

    name: str
    damage: float
    energy_gain: float
    turns: int

    def __post_init__(self) -> None:
        if self.damage < 0:
            raise ValueError("Fast move damage cannot be negative.")
        if self.energy_gain <= 0:
            raise ValueError("Fast move energy gain must be positive.")
        if self.turns <= 0:
            raise ValueError("Fast move duration (turns) must be positive.")


@dataclass(frozen=True)
class PvpChargeMove:
    """Container describing a PvP charge move."""

    name: str
    damage: float
    energy_cost: float
    reliability: float | None = None
    has_buff: bool = False

    def __post_init__(self) -> None:
        if self.damage < 0:
            raise ValueError("Charge move damage cannot be negative.")
        if self.energy_cost <= 0:
            raise ValueError("Charge move energy cost must be positive.")
        if self.reliability is not None and self.reliability < 0:
            raise ValueError("Charge move reliability must be non-negative when provided.")

    @property
    def effective_reliability(self) -> float:
        """Return the reliability, defaulting to the inverse energy cost."""

        if self.reliability is not None:
            return self.reliability
        return 1.0 / self.energy_cost


@dataclass(frozen=True)
class LeagueConfig:
    """Encapsulates scoring defaults for a PvP league."""

    cp_cap: int | None
    stat_product_reference: float
    move_pressure_reference: float
    bait_probability: float


DEFAULT_BETA = 0.52
FAST_MOVE_ENERGY_WEIGHT = 0.35
BUFF_WEIGHT = 12.0

DEFAULT_LEAGUE_CONFIGS: Mapping[str, LeagueConfig] = {
    "great": LeagueConfig(
        cp_cap=1500,
        stat_product_reference=1_600_000.0,
        move_pressure_reference=48.0,
        bait_probability=0.55,
    ),
    "ultra": LeagueConfig(
        cp_cap=2500,
        stat_product_reference=2_400_000.0,
        move_pressure_reference=52.0,
        bait_probability=0.5,
    ),
    "master": LeagueConfig(
        cp_cap=None,
        stat_product_reference=3_000_000.0,
        move_pressure_reference=56.0,
        bait_probability=0.45,
    ),
}


def stat_product(attack: float, defense: float, stamina: int) -> float:
    """Compute the stat product ``A * D * H`` from the PvP specification."""

    if attack <= 0 or defense <= 0 or stamina <= 0:
        raise ValueError("Stats must be positive to compute stat product.")
    return attack * defense * stamina


def normalise(value: float, reference: float) -> float:
    """Normalise ``value`` by dividing by a strictly positive ``reference``."""

    if reference <= 0:
        raise ValueError("Reference value must be positive for normalisation.")
    return value / reference


def fast_move_pressure(
    fast_move: PvpFastMove,
    *,
    energy_weight: float = FAST_MOVE_ENERGY_WEIGHT,
) -> float:
    """Compute the fast move pressure term ``FMP`` from the specification."""

    if energy_weight < 0:
        raise ValueError("Energy weight must be non-negative.")
    turns_seconds = fast_move.turns * 0.5
    damage_term = fast_move.damage / turns_seconds
    energy_term = energy_weight * (fast_move.energy_gain / turns_seconds)
    return damage_term + energy_term


def charge_move_pressure(
    charge_move: PvpChargeMove,
    *,
    buff_weight: float = BUFF_WEIGHT,
) -> float:
    """Compute ``CPP_c`` for a single charge move."""

    if buff_weight < 0:
        raise ValueError("Buff weight must be non-negative.")
    buff_term = buff_weight if charge_move.has_buff else 0.0
    return charge_move.effective_reliability * (charge_move.damage + buff_term)


def pair_charge_pressure(
    high_energy_move: PvpChargeMove,
    low_energy_move: PvpChargeMove,
    *,
    bait_probability: float,
    buff_weight: float = BUFF_WEIGHT,
) -> float:
    """Compute the baited charge pressure ``CPP_pair`` for two charge moves."""

    if not 0.0 <= bait_probability <= 1.0:
        raise ValueError("Bait probability must lie within [0, 1].")
    high = charge_move_pressure(high_energy_move, buff_weight=buff_weight)
    low = charge_move_pressure(low_energy_move, buff_weight=buff_weight)
    return (bait_probability * high) + ((1.0 - bait_probability) * low)


def move_pressure(
    fast_move: PvpFastMove,
    charge_moves: Sequence[PvpChargeMove],
    *,
    bait_probability: float,
    energy_weight: float = FAST_MOVE_ENERGY_WEIGHT,
    buff_weight: float = BUFF_WEIGHT,
) -> float:
    """Compute total move pressure ``MP`` according to the specification."""

    if not charge_moves:
        raise ValueError("At least one charge move is required to compute move pressure.")

    fast_component = fast_move_pressure(fast_move, energy_weight=energy_weight)
    charge_components = [
        charge_move_pressure(move, buff_weight=buff_weight) for move in charge_moves
    ]
    best_charge = max(charge_components)

    if len(charge_moves) >= 2:
        sorted_moves = sorted(charge_moves, key=lambda move: move.energy_cost)
        bait_component = pair_charge_pressure(
            high_energy_move=sorted_moves[-1],
            low_energy_move=sorted_moves[0],
            bait_probability=bait_probability,
            buff_weight=buff_weight,
        )
        best_charge = max(best_charge, bait_component)

    return fast_component + best_charge


def compute_pvp_score(
    attack: float,
    defense: float,
    stamina: int,
    fast_move: PvpFastMove,
    charge_moves: Sequence[PvpChargeMove],
    *,
    league: str = "great",
    beta: float | None = None,
    stat_product_reference: float | None = None,
    move_pressure_reference: float | None = None,
    bait_probability: float | None = None,
    energy_weight: float = FAST_MOVE_ENERGY_WEIGHT,
    buff_weight: float = BUFF_WEIGHT,
    league_configs: Mapping[str, LeagueConfig] = DEFAULT_LEAGUE_CONFIGS,
) -> dict[str, float]:
    """Compute the PvP score dictionary for a Pokémon build."""

    if beta is not None and not 0.0 < beta < 1.0:
        raise ValueError("Beta must lie strictly between 0 and 1 when provided.")

    key = league.lower()
    if key not in league_configs:
        raise KeyError(f"Unknown league '{league}'. Available: {sorted(league_configs)}")

    config = league_configs[key]
    beta_value = beta if beta is not None else DEFAULT_BETA
    sp_reference = (
        stat_product_reference
        if stat_product_reference is not None
        else config.stat_product_reference
    )
    mp_reference = (
        move_pressure_reference
        if move_pressure_reference is not None
        else config.move_pressure_reference
    )
    bait_prob = (
        bait_probability if bait_probability is not None else config.bait_probability
    )

    stat_prod = stat_product(attack, defense, stamina)
    stat_prod_norm = normalise(stat_prod, sp_reference)
    mp = move_pressure(
        fast_move,
        charge_moves,
        bait_probability=bait_prob,
        energy_weight=energy_weight,
        buff_weight=buff_weight,
    )
    mp_norm = normalise(mp, mp_reference)
    score = (stat_prod_norm ** beta_value) * (mp_norm ** (1.0 - beta_value))

    return {
        "stat_product": stat_prod,
        "stat_product_normalised": stat_prod_norm,
        "move_pressure": mp,
        "move_pressure_normalised": mp_norm,
        "score": score,
    }
