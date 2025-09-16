"""REST API for exposing :func:`pogo_analyzer.vision.scan_screenshot`."""
from __future__ import annotations

import imghdr
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Tuple

from .errors import (
    DependencyError,
    InputValidationError,
    PayloadTooLargeError,
    PogoAnalyzerError,
    ProcessingError,
)
from .observability import (
    configure_logging,
    generate_trace_id,
    get_logger,
    health_snapshot,
    metrics,
    render_metrics,
)
from .vision import scan_screenshot

try:  # pragma: no cover - optional dependency
    from fastapi import FastAPI, File, Request, UploadFile  # type: ignore[import-not-found]
    from fastapi.encoders import jsonable_encoder  # type: ignore[import-not-found]
    from fastapi.responses import JSONResponse, PlainTextResponse  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - gracefully handled at runtime
    FastAPI = None  # type: ignore
    File = None  # type: ignore
    Request = None  # type: ignore
    UploadFile = None  # type: ignore
    jsonable_encoder = None  # type: ignore
    JSONResponse = None  # type: ignore
    PlainTextResponse = None  # type: ignore


LOGGER = get_logger(__name__)


_IMAGE_CONTENT_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/webp": "webp",
}

_ALLOWED_IMAGE_FORMATS: Dict[str, str] = {
    "png": ".png",
    "jpeg": ".jpg",
    "webp": ".webp",
}

_MAX_UPLOAD_SIZE_MB = 5
_MAX_UPLOAD_SIZE = _MAX_UPLOAD_SIZE_MB * 1024 * 1024

_SECURE_HEADERS: Dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
}


def _validate_image_upload(data: bytes, *, declared_type: str) -> Tuple[str, str]:
    """Validate the uploaded image payload and return the detected format and suffix."""

    if len(data) > _MAX_UPLOAD_SIZE:
        raise PayloadTooLargeError(
            f"Uploaded file exceeds {_MAX_UPLOAD_SIZE_MB} MB limit.",
            remediation="Resize the screenshot before uploading.",
            context={"declared_type": declared_type, "size_bytes": len(data)},
        )

    detected_format = imghdr.what(None, data)
    if detected_format is None or detected_format not in _ALLOWED_IMAGE_FORMATS:
        raise InputValidationError(
            "Unsupported or corrupted image upload.",
            remediation="Ensure the file is a valid PNG, JPEG, or WEBP screenshot.",
            context={"declared_type": declared_type},
        )

    expected_format = _IMAGE_CONTENT_TYPES.get(declared_type)
    if expected_format and detected_format != expected_format:
        raise InputValidationError(
            "Uploaded file content does not match declared image type.",
            remediation="Verify the file extension and content type before retrying.",
            context={
                "declared_type": declared_type,
                "detected_format": detected_format,
            },
        )

    return detected_format, _ALLOWED_IMAGE_FORMATS[detected_format]


def _validate_dependency() -> None:
    if FastAPI is None:
        raise DependencyError(
            "FastAPI is required to use pogo_analyzer.api.",
            remediation="Install fastapi and uvicorn to expose the scan endpoint.",
        )


def create_app() -> "FastAPI":
    """Return a configured FastAPI application exposing screenshot analysis."""

    _validate_dependency()
    assert FastAPI is not None  # for mypy

    configure_logging()

    app = FastAPI(title="Pokémon Analyzer", version="1.0.0")

    assert Request is not None  # for mypy

    @app.middleware("http")
    async def add_security_headers(request: "Request", call_next):  # type: ignore[override]
        response = await call_next(request)
        for header, value in _SECURE_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

    @app.get("/health", tags=["system"])
    async def healthcheck() -> Dict[str, Any]:
        return health_snapshot()

    assert PlainTextResponse is not None  # for mypy

    @app.get("/metrics", tags=["system"], response_class=PlainTextResponse)
    async def metrics_endpoint() -> "PlainTextResponse":
        return PlainTextResponse(render_metrics(), media_type="text/plain; version=0.0.4")

    @app.post("/scan", tags=["analysis"])
    async def scan_endpoint(file: UploadFile = File(...)) -> "JSONResponse":  # type: ignore[valid-type]
        assert UploadFile is not None and JSONResponse is not None

        trace_id = generate_trace_id()
        metrics.increment("pogo_analyzer_scan_requests_total")
        start_time = time.perf_counter()
        tmp_path: Path | None = None

        try:
            if not file.content_type or file.content_type.lower() not in _IMAGE_CONTENT_TYPES:
                raise InputValidationError(
                    "Only image uploads are supported.",
                    remediation="Submit a PNG, JPEG, or WEBP screenshot.",
                    context={"provided_type": file.content_type},
                )

            declared_type = file.content_type.lower()
            data = await file.read()
        except InputValidationError as exc:
            metrics.increment("pogo_analyzer_scan_failures_total")
            LOGGER.warning(
                "scan_validation_failed",
                extra={"event": "scan_validation_failed", "trace_id": trace_id, "error": exc.to_payload()},
            )
            response = JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.to_payload(trace_id=trace_id)},
            )
            response.headers["X-Trace-Id"] = trace_id
            return response
        except Exception as exc:  # pragma: no cover - unexpected read failure
            metrics.increment("pogo_analyzer_scan_failures_total")
            LOGGER.exception(
                "scan_read_failed",
                extra={"event": "scan_read_failed", "trace_id": trace_id},
            )
            response = JSONResponse(
                status_code=ProcessingError.http_status,
                content={
                    "error": ProcessingError(
                        "Failed to read the uploaded file.",
                        remediation="Retry the upload or capture a new screenshot.",
                    ).to_payload(trace_id=trace_id)
                },
            )
            response.headers["X-Trace-Id"] = trace_id
            return response

        if not data:
            exc = InputValidationError(
                "Uploaded file is empty.",
                remediation="Capture a fresh screenshot and retry.",
            )
            metrics.increment("pogo_analyzer_scan_failures_total")
            LOGGER.warning(
                "scan_validation_failed",
                extra={"event": "scan_validation_failed", "trace_id": trace_id, "error": exc.to_payload()},
            )
            response = JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.to_payload(trace_id=trace_id)},
            )
            response.headers["X-Trace-Id"] = trace_id
            return response

        try:
            _, suffix = _validate_image_upload(data, declared_type=declared_type)
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(data)
                tmp_path = Path(tmp.name)
            result = scan_screenshot(tmp_path)
        except InputValidationError as exc:
            metrics.increment("pogo_analyzer_scan_failures_total")
            LOGGER.warning(
                "scan_validation_failed",
                extra={"event": "scan_validation_failed", "trace_id": trace_id, "error": exc.to_payload()},
            )
            response = JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.to_payload(trace_id=trace_id)},
            )
            response.headers["X-Trace-Id"] = trace_id
            return response
        except PogoAnalyzerError as exc:
            metrics.increment("pogo_analyzer_scan_failures_total")
            LOGGER.warning(
                "scan_failed",
                extra={
                    "event": "scan_failed",
                    "trace_id": trace_id,
                    "error": exc.to_payload(),
                },
            )
            response = JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.to_payload(trace_id=trace_id)},
            )
            response.headers["X-Trace-Id"] = trace_id
            return response
        except Exception as exc:
            metrics.increment("pogo_analyzer_scan_failures_total")
            LOGGER.exception(
                "scan_unhandled_error",
                extra={"event": "scan_unhandled_error", "trace_id": trace_id},
            )
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "category": "internal_error",
                        "message": "Unexpected error while processing screenshot.",
                        "remediation": "Retry the request or contact support with the trace identifier.",
                        "trace_id": trace_id,
                    }
                },
            )
            response.headers["X-Trace-Id"] = trace_id
            return response
        finally:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink()

        payload: Dict[str, Any]
        if jsonable_encoder is not None:
            payload = jsonable_encoder(result)
        else:  # pragma: no cover - jsonable_encoder always available with FastAPI
            payload = dict(result)
            ivs = payload.get("ivs")
            if isinstance(ivs, tuple):
                payload["ivs"] = list(ivs)

        response = JSONResponse(content=payload)
        duration = time.perf_counter() - start_time
        metrics.observe("pogo_analyzer_scan_duration_seconds", duration)
        LOGGER.info(
            "scan_completed",
            extra={
                "event": "scan_completed",
                "trace_id": trace_id,
                "declared_type": declared_type,
                "bytes": len(data),
                "duration": round(duration, 4),
            },
        )
        response.headers["X-Trace-Id"] = trace_id
        return response

    return app


try:  # pragma: no cover - optional when module imported for app discovery
    app = create_app()
except DependencyError:  # FastAPI missing
    app = None  # type: ignore


__all__ = ["create_app", "app"]
