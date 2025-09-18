"""Backward-compatible re-export for the simple table implementation."""

from __future__ import annotations

from .tables.simple_table import Row, SimpleSeries, SimpleTable

__all__ = ["Row", "SimpleSeries", "SimpleTable"]
