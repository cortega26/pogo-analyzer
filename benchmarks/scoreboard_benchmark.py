"""Synthetic benchmark for PoGo Analyzer scoreboard row generation."""

from __future__ import annotations

import statistics
from time import perf_counter

from pogo_analyzer.data import PokemonRaidEntry, build_entry_rows
from pogo_analyzer.data.raid_entries import _entry_row_items as _cached_entry_row_items


def baseline_build_entry_rows(
    entries: list[PokemonRaidEntry],
) -> list[dict[str, object]]:
    """Replicate the pre-optimization behaviour for comparison."""

    return [entry.to_row() for entry in entries]


def synthetic_entries(count: int) -> list[PokemonRaidEntry]:
    """Generate a deterministic pool of raid entries for benchmarks."""

    entries: list[PokemonRaidEntry] = []
    for idx in range(count):
        attack = idx % 16
        defence = (idx * 3) % 16
        stamina = (idx * 5) % 16
        entries.append(
            PokemonRaidEntry(
                name=f"Benchmark {idx}",
                ivs=(attack, defence, stamina),
                final_form="Mega Benchmark",
                role="Synthetic",
                base=70 + (idx % 30),
                lucky=bool(idx % 2),
                shadow=bool((idx // 2) % 2),
                needs_tm=idx % 3 == 0,
                mega_now=idx % 5 == 0,
                mega_soon=idx % 7 == 0,
                notes="Synthetic benchmark entry",
            )
        )
    return entries


def time_runs(func, iterations: int) -> tuple[float, float]:
    """Return (min, mean) execution time across ``iterations`` invocations."""

    durations: list[float] = []
    for _ in range(iterations):
        start = perf_counter()
        func()
        durations.append(perf_counter() - start)
    return min(durations), statistics.mean(durations)


def main() -> None:
    entries = synthetic_entries(5000)
    repetitions = 25

    # Baseline timings (mirrors old implementation behaviour)
    baseline_first_start = perf_counter()
    baseline_build_entry_rows(entries)
    baseline_first = perf_counter() - baseline_first_start
    baseline_min, baseline_mean = time_runs(
        lambda: baseline_build_entry_rows(entries), repetitions
    )

    # Optimised implementation timings
    _cached_entry_row_items.cache_clear()
    cached_first_start = perf_counter()
    build_entry_rows(entries)
    cached_first = perf_counter() - cached_first_start
    cached_min, cached_mean = time_runs(lambda: build_entry_rows(entries), repetitions)

    print(f"Baseline first run: {baseline_first:.6f}s")
    print(
        f"Baseline min/mean over {repetitions:d} runs: {baseline_min:.6f}s / {baseline_mean:.6f}s"
    )
    print(f"Optimised first run: {cached_first:.6f}s")
    print(
        f"Optimised min/mean over {repetitions:d} runs: {cached_min:.6f}s / {cached_mean:.6f}s"
    )
    if cached_mean:
        print(f"Steady-state speed-up: {baseline_mean / cached_mean:.2f}x")


if __name__ == "__main__":
    main()
