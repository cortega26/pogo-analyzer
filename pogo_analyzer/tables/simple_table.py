"""Minimal table structures that emulate a subset of pandas' interface.

The goal is API compatibility with the portions of ``pandas.DataFrame`` that the
scoreboard scripts rely on—mainly sorting, indexing, CSV export, and string
representation. When pandas is installed the real DataFrame is used instead, so
``SimpleTable`` purposefully keeps the surface area small and predictable.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import Any, Callable

Row = dict[str, Any]


class SimpleSeries:
    """Minimal :class:`pandas.Series` stand-in used when pandas is unavailable."""

    def __init__(self, data: Iterable[Any]):
        """Materialise the provided iterable so repeated iteration is safe."""

        self._data = list(data)

    def apply(self, func: Callable[[Any], Any]) -> SimpleSeries:
        """Return a new series with ``func`` applied to each element."""

        return SimpleSeries(func(item) for item in self._data)

    def to_list(self) -> list[Any]:
        """Return the series contents as a list copy."""

        return list(self._data)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


class SimpleTable:
    """Lightweight, pandas-like table to keep scripts functional without pandas."""

    def __init__(self, rows: Sequence[Row], columns: Sequence[str] | None = None):
        """Normalise row data and column order.

        Parameters
        ----------
        rows:
            Sequence of dictionaries representing table rows. Missing keys are
            filled with empty strings.
        columns:
            Optional explicit column order. Unlisted keys discovered in ``rows``
            are appended so that no data is dropped.
        """

        self._rows = [dict(row) for row in rows]
        discovered_columns: list[str] = []
        discovered_set: set[str] = set()
        for row in self._rows:
            for key in row.keys():
                # Preserve discovery order so generated tables match pandas'
                # column ordering when fed the same dictionaries.
                if key not in discovered_set:
                    discovered_columns.append(key)
                    discovered_set.add(key)
        if columns is None:
            final_columns: list[str] = list(discovered_columns)
        else:
            final_columns = list(columns)
            column_set = set(final_columns)
            for key in discovered_columns:
                if key not in column_set:
                    final_columns.append(key)
                    column_set.add(key)
        self._columns: list[str] = list(final_columns)
        self._column_set: set[str] = set(self._columns)
        for row in self._rows:
            for column in self._columns:
                row.setdefault(column, "")

    def sort_values(self, by: str, ascending: bool = True) -> SimpleTable:
        """Return a table sorted by ``by``; mirrors ``DataFrame.sort_values``."""

        if by not in self._column_set:
            raise KeyError(f"Column '{by}' does not exist.")
        reverse = not ascending
        sorted_rows = sorted(self._rows, key=lambda item: item[by], reverse=reverse)
        return SimpleTable(sorted_rows, self._columns)

    def reset_index(self, drop: bool = False) -> SimpleTable:
        """Return a table with a reset positional index.

        When ``drop`` is ``False`` (the default) a positional column mirroring
        pandas' behaviour is prepended without clobbering existing data.
        """

        if drop:
            return SimpleTable(self._rows, self._columns)

        existing_columns = list(self._columns)
        available = set(self._column_set)
        index_name = "index"
        if index_name in available:
            suffix = 0
            while True:
                candidate = f"level_{suffix}"
                if candidate not in available:
                    index_name = candidate
                    break
                suffix += 1

        indexed_rows: list[Row] = []
        for idx, row in enumerate(self._rows):
            new_row = dict(row)
            new_row[index_name] = idx
            indexed_rows.append(new_row)

        columns = [index_name] + existing_columns
        return SimpleTable(indexed_rows, columns)

    def __getitem__(self, key: str) -> SimpleSeries:
        """Return a :class:`SimpleSeries` for the requested column."""

        if key not in self._column_set:
            raise KeyError(key)
        return SimpleSeries(row[key] for row in self._rows)

    def __setitem__(self, key: str, value: Iterable[Any]) -> None:
        """Assign ``value`` to ``key``, matching ``pandas.DataFrame`` semantics."""

        if isinstance(value, SimpleSeries):
            values = value.to_list()
        else:
            values = list(value)
        if len(values) != len(self._rows):
            raise ValueError("Column length mismatch.")
        for row, val in zip(self._rows, values):
            row[key] = val
        if key not in self._column_set:
            self._columns.append(key)
            self._column_set.add(key)

    def to_csv(
        self, path: Path, index: bool = False
    ) -> None:  # noqa: ARG002 - parity with pandas signature
        """Write the table to ``path`` in UTF-8 CSV format."""

        with Path(path).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self._columns)
            writer.writeheader()
            writer.writerows(self._rows)

    def to_excel(
        self, path: Path, index: bool = False
    ) -> None:  # noqa: ARG002 - parity with pandas signature
        """Mimic ``DataFrame.to_excel`` but raise when pandas is absent."""

        raise RuntimeError("Excel export requires pandas to be installed.")

    def head(self, n: int) -> SimpleTable:
        """Return the first ``n`` rows, similar to ``DataFrame.head``."""

        return SimpleTable(self._rows[:n], self._columns)

    def to_string(self, index: bool = True) -> str:
        """Render the table as a string suitable for console previews."""

        if not self._rows:
            return ""
        columns = list(self._columns)
        data = [[str(row.get(col, "")) for col in columns] for row in self._rows]
        if index:
            index_width = max(len(str(len(data) - 1)), len("index"))
            index_header = "index"
            headers = [index_header] + columns
            widths = [index_width] + [len(col) for col in columns]
            rows = [[str(i)] + row for i, row in enumerate(data)]
        else:
            headers = columns
            widths = [len(col) for col in columns]
            rows = data
        for row in rows:
            for idx, cell in enumerate(row):
                widths[idx] = max(widths[idx], len(cell))
        header_line = "  ".join(
            title.ljust(widths[idx]) for idx, title in enumerate(headers)
        ).rstrip()
        line_items = [header_line]
        for row in rows:
            line_items.append(
                "  ".join(
                    cell.ljust(widths[idx]) for idx, cell in enumerate(row)
                ).rstrip()
            )
        return "\n".join(line_items)


__all__ = ["Row", "SimpleSeries", "SimpleTable"]
