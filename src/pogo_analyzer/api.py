"""REST API for exposing :func:`pogo_analyzer.vision.scan_screenshot`."""
from __future__ import annotations

import imghdr
import tempfile
from pathlib import Path
from typing import Any, Dict, Tuple

from .vision import scan_screenshot

try:  # pragma: no cover - optional dependency
    from fastapi import FastAPI, File, HTTPException, Request, UploadFile  # type: ignore[import-not-found]
    from fastapi.encoders import jsonable_encoder  # type: ignore[import-not-found]
    from fastapi.responses import JSONResponse  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - gracefully handled at runtime
    FastAPI = None  # type: ignore
    File = None  # type: ignore
    HTTPException = None  # type: ignore
    Request = None  # type: ignore
    UploadFile = None  # type: ignore
    jsonable_encoder = None  # type: ignore
    JSONResponse = None  # type: ignore


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

    assert HTTPException is not None  # pragma: no cover - ensured by dependency validation

    if len(data) > _MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds {_MAX_UPLOAD_SIZE_MB} MB limit.",
        )

    detected_format = imghdr.what(None, data)
    if detected_format is None or detected_format not in _ALLOWED_IMAGE_FORMATS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported or corrupted image upload.",
        )

    expected_format = _IMAGE_CONTENT_TYPES.get(declared_type)
    if expected_format and detected_format != expected_format:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file content does not match declared image type.",
        )

    return detected_format, _ALLOWED_IMAGE_FORMATS[detected_format]


def _validate_dependency() -> None:
    if FastAPI is None:
        raise RuntimeError(
            "FastAPI is required to use pogo_analyzer.api. Install fastapi to expose the"
            " scan endpoint."
        )


def create_app() -> "FastAPI":
    """Return a configured FastAPI application exposing screenshot analysis."""

    _validate_dependency()
    assert FastAPI is not None  # for mypy

    app = FastAPI(title="Pokémon Analyzer", version="1.0.0")

    assert Request is not None  # for mypy

    @app.middleware("http")
    async def add_security_headers(request: "Request", call_next):  # type: ignore[override]
        response = await call_next(request)
        for header, value in _SECURE_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

    @app.get("/health", tags=["system"])
    async def healthcheck() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/scan", tags=["analysis"])
    async def scan_endpoint(file: UploadFile = File(...)) -> "JSONResponse":  # type: ignore[valid-type]
        assert UploadFile is not None and JSONResponse is not None and HTTPException is not None

        if not file.content_type or file.content_type.lower() not in _IMAGE_CONTENT_TYPES:
            raise HTTPException(status_code=400, detail="Only image uploads are supported.")

        declared_type = file.content_type.lower()
        try:
            data = await file.read()
        except Exception as exc:  # pragma: no cover - exercised in error handling tests
            raise HTTPException(status_code=400, detail=f"Failed to read upload: {exc}") from exc

        if not data:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        _, suffix = _validate_image_upload(data, declared_type=declared_type)
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(data)
                tmp_path = Path(tmp.name)
            result = scan_screenshot(tmp_path)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
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

        return JSONResponse(content=payload)

    return app


try:  # pragma: no cover - optional when module imported for app discovery
    app = create_app()
except RuntimeError:  # FastAPI missing
    app = None  # type: ignore


__all__ = ["create_app", "app"]
