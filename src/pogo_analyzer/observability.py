"""Logging, metrics, and health tooling for pogo_analyzer."""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Tuple

from .errors import sanitize_context

__all__ = [
    "configure_logging",
    "get_logger",
    "metrics",
    "metrics_snapshot",
    "render_metrics",
    "health_snapshot",
    "generate_trace_id",
]


_STANDARD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())
_LOGGER_NAME = "pogo_analyzer"
_CONFIGURED = False
_LOCK = threading.Lock()


class StructuredLogFormatter(logging.Formatter):
    """Format log records as structured JSON strings."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - exercised via tests
        message = record.getMessage()
        event = getattr(record, "event", None) or "log"
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": event,
            "message": message,
        }

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_ATTRS and key not in {"message", "asctime"}
        }
        if extras:
            payload["context"] = sanitize_context(extras)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def configure_logging(level: int | str | None = None) -> logging.Logger:
    """Configure structured logging once and return the package logger."""

    global _CONFIGURED
    with _LOCK:
        logger = logging.getLogger(_LOGGER_NAME)
        if not _CONFIGURED:
            handler = logging.StreamHandler()
            handler.setFormatter(StructuredLogFormatter())
            logger.addHandler(handler)
            logger.propagate = False
            _CONFIGURED = True
        if level is not None:
            logger.setLevel(level if isinstance(level, int) else logging.getLevelName(level))
        elif logger.level == logging.NOTSET:
            logger.setLevel(logging.INFO)
    return logging.getLogger(_LOGGER_NAME)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger with structured configuration."""

    configure_logging()
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)


class MetricsRegistry:
    """Thread-safe, in-process metrics collector with Prometheus rendering."""

    def __init__(self) -> None:
        self._metadata: Dict[str, Tuple[str, str]] = {}
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._summaries: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def register_counter(self, name: str, description: str) -> None:
        self._metadata[name] = ("counter", description)

    def register_gauge(self, name: str, description: str) -> None:
        self._metadata[name] = ("gauge", description)
        self._gauges.setdefault(name, 0.0)

    def register_summary(self, name: str, description: str) -> None:
        self._metadata[name] = ("summary", description)
        self._summaries.setdefault(name, [])

    def increment(self, name: str, amount: float = 1.0) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + amount

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            bucket = self._summaries.setdefault(name, [])
            bucket.append(value)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "summaries": {key: list(values) for key, values in self._summaries.items()},
            }

    def render_prometheus(self) -> str:
        lines: List[str] = []
        snapshot = self.snapshot()
        for name, (metric_type, description) in self._metadata.items():
            lines.append(f"# HELP {name} {description}")
            lines.append(f"# TYPE {name} {metric_type}")
            if metric_type == "counter":
                value = snapshot["counters"].get(name, 0.0)
                lines.append(f"{name} {value}")
            elif metric_type == "gauge":
                value = snapshot["gauges"].get(name, 0.0)
                lines.append(f"{name} {value}")
            elif metric_type == "summary":
                values = snapshot["summaries"].get(name, [])
                count = float(len(values))
                total = float(sum(values))
                average = total / count if count else 0.0
                lines.append(f"{name}_count {count}")
                lines.append(f"{name}_sum {total}")
                lines.append(f"{name}_avg {average}")
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()
metrics.register_counter(
    "pogo_analyzer_scan_requests_total", "Total scan requests processed.")
metrics.register_counter(
    "pogo_analyzer_scan_failures_total", "Total scan requests that failed.")
metrics.register_summary(
    "pogo_analyzer_scan_duration_seconds", "Scan request duration in seconds.")
metrics.register_gauge(
    "pogo_analyzer_dependency_ready", "1 when critical dependencies are available.")


def metrics_snapshot() -> Dict[str, Any]:
    """Return a simple dictionary snapshot of the in-process metrics."""

    return metrics.snapshot()


def render_metrics() -> str:
    """Render metrics in Prometheus exposition format."""

    return metrics.render_prometheus()


def _dependency_status() -> Dict[str, Any]:
    try:
        from . import vision
    except Exception:  # pragma: no cover - import error is unexpected
        return {"vision_module": False, "reason": "vision import failed"}

    status = {
        "pillow": vision.Image is not None,
        "pytesseract": vision.pytesseract is not None,
    }
    metrics.set_gauge(
        "pogo_analyzer_dependency_ready",
        1.0 if all(status.values()) else 0.0,
    )
    return status


def _cache_status() -> Dict[str, Any]:
    from . import vision

    return {
        "stats_cache_loaded": vision._STATS_CACHE is not None,
        "species_index_loaded": vision._SPECIES_INDEX is not None,
        "form_index_loaded": vision._FORM_INDEX is not None,
    }


def health_snapshot() -> Dict[str, Any]:
    """Return a structured health snapshot for the API health endpoint."""

    dependency = _dependency_status()
    status = "ok" if all(dependency.values()) else "degraded"
    snapshot = {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "dependencies": dependency,
            "caches": _cache_status(),
        },
        "metrics": metrics_snapshot(),
    }
    return snapshot


def generate_trace_id() -> str:
    """Generate a short-lived trace identifier suitable for user feedback."""

    return uuid.uuid4().hex[:12]
