"""Configuration helpers for raid scoreboard exports."""

from __future__ import annotations

import os
from argparse import Namespace
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

__all__ = ["ScoreboardExportConfig", "build_export_config"]


@dataclass(frozen=True)
class ScoreboardExportConfig:
    """Configuration describing how scoreboard exports should be produced."""

    csv_path: Path
    excel_path: Path | None
    preview_limit: int = 10

    def __post_init__(self) -> None:
        if self.preview_limit <= 0:
            raise ValueError("preview_limit must be a positive integer.")

    @property
    def excel_requested(self) -> bool:
        """Return ``True`` when an Excel file should be attempted."""

        return self.excel_path is not None


def _truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_output_path(base_dir: Path, value: str | Path) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()


def build_export_config(
    args: Namespace,
    env: Mapping[str, str] | None = None,
) -> ScoreboardExportConfig:
    """Construct export settings by merging CLI arguments and environment variables."""

    env = env or os.environ
    if args.output_dir is not None:
        base_dir = Path(args.output_dir).expanduser()
    else:
        env_dir = env.get("RAID_SCOREBOARD_OUTPUT_DIR")
        base_dir = Path(env_dir).expanduser() if env_dir else Path.cwd()

    csv_name = args.csv_name or env.get("RAID_SCOREBOARD_CSV") or "raid_scoreboard.csv"
    csv_path = _resolve_output_path(base_dir, csv_name)

    disable_excel = args.no_excel or _truthy(env.get("RAID_SCOREBOARD_DISABLE_EXCEL"))
    if disable_excel:
        excel_path = None
    else:
        excel_name = (
            args.excel_name
            or env.get("RAID_SCOREBOARD_EXCEL")
            or "raid_scoreboard.xlsx"
        )
        excel_path = _resolve_output_path(base_dir, excel_name)

    preview_limit = args.preview_limit
    if preview_limit is None:
        preview_env = env.get("RAID_SCOREBOARD_PREVIEW_LIMIT")
        if preview_env is not None:
            try:
                preview_limit = int(preview_env)
            except ValueError as exc:  # pragma: no cover - defensive guard.
                raise ValueError(
                    "RAID_SCOREBOARD_PREVIEW_LIMIT must be an integer."
                ) from exc
    if preview_limit is None:
        preview_limit = 10
    if preview_limit <= 0:
        raise ValueError("preview_limit must be a positive integer.")

    return ScoreboardExportConfig(
        csv_path=csv_path, excel_path=excel_path, preview_limit=preview_limit
    )
