"""Microbenchmark for the pandas fallback SimpleTable implementation."""

from __future__ import annotations

import argparse
import statistics
import time
from typing import List

from pogo_analyzer.simple_table import Row, SimpleTable


def build_rows(num_rows: int, num_cols: int) -> List[Row]:
    """Construct synthetic rows with deterministic data."""

    template = {f"col{i}": i for i in range(num_cols)}
    rows: List[Row] = []
    for r in range(num_rows):
        row = {key: (value + r) % num_cols for key, value in template.items()}
        rows.append(row)
    return rows


def run_benchmark(num_rows: int, num_cols: int, repeats: int) -> None:
    rows = build_rows(num_rows, num_cols)
    timings = []
    for _ in range(repeats):
        start = time.perf_counter()
        SimpleTable(rows)
        timings.append(time.perf_counter() - start)
    median = statistics.median(timings)
    avg = statistics.mean(timings)
    print(
        "SimpleTable init: rows={:,} cols={} repeats={} median={:.6f}s mean={:.6f}s".format(
            num_rows, num_cols, repeats, median, avg
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=5000, help="Number of synthetic rows")
    parser.add_argument("--cols", type=int, default=40, help="Number of synthetic columns")
    parser.add_argument("--repeats", type=int, default=5, help="Number of benchmark repetitions")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_benchmark(args.rows, args.cols, args.repeats)
