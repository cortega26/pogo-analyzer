"""Centralised error taxonomy for pogo_analyzer."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

__all__ = [
    "PogoAnalyzerError",
    "DependencyError",
    "InputValidationError",
    "ProcessingError",
    "OperationalError",
    "NotReadyError",
    "PayloadTooLargeError",
    "sanitize_context",
]


_SENSITIVE_KEYS = {
    "player_name",
    "trainer_name",
    "username",
    "email",
    "token",
    "session",
    "password",
    "auth",
    "authorization",
}


def _mask_string(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}***{value[-2:]}"


def _sanitize_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if isinstance(value, Mapping):
        return sanitize_context(value)
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]
    if lowered in _SENSITIVE_KEYS:
        if isinstance(value, str):
            return _mask_string(value)
        return "***"
    return value


def sanitize_context(context: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a sanitised copy of contextual logging or error data."""

    return {key: _sanitize_value(key, value) for key, value in context.items()}


@dataclass
class PogoAnalyzerError(Exception):
    """Base class for structured, actionable errors raised by the package."""

    message: str
    remediation: str | None = None
    context: Dict[str, Any] | None = None
    category: str = "internal_error"
    http_status: int = 500

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        super().__init__(self.message)

    def to_payload(self, *, trace_id: str | None = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "category": self.category,
            "message": self.message,
        }
        if self.remediation:
            payload["remediation"] = self.remediation
        if self.context:
            payload["context"] = sanitize_context(self.context)
        if trace_id:
            payload["trace_id"] = trace_id
        return payload


class DependencyError(PogoAnalyzerError):
    category = "dependency_error"
    http_status = 503


class InputValidationError(PogoAnalyzerError):
    category = "input_error"
    http_status = 400


class PayloadTooLargeError(InputValidationError):
    category = "payload_too_large"
    http_status = 413


class ProcessingError(PogoAnalyzerError):
    category = "processing_error"
    http_status = 422


class OperationalError(PogoAnalyzerError):
    category = "operational_error"
    http_status = 500


class NotReadyError(PogoAnalyzerError):
    category = "not_ready"
    http_status = 503
