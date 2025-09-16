"""REST API for exposing :func:`pogo_analyzer.vision.scan_screenshot`."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict

from .vision import scan_screenshot

try:  # pragma: no cover - optional dependency
    from fastapi import FastAPI, File, HTTPException, UploadFile
    from fastapi.encoders import jsonable_encoder
    from fastapi.responses import JSONResponse
except Exception:  # pragma: no cover - gracefully handled at runtime
    FastAPI = None  # type: ignore
    File = None  # type: ignore
    HTTPException = None  # type: ignore
    UploadFile = None  # type: ignore
    jsonable_encoder = None  # type: ignore
    JSONResponse = None  # type: ignore


_IMAGE_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}


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

    @app.get("/health", tags=["system"])
    async def healthcheck() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/scan", tags=["analysis"])
    async def scan_endpoint(file: UploadFile = File(...)) -> "JSONResponse":  # type: ignore[valid-type]
        assert UploadFile is not None and JSONResponse is not None and HTTPException is not None

        if file.content_type and file.content_type.lower() not in _IMAGE_CONTENT_TYPES:
            raise HTTPException(status_code=400, detail="Only image uploads are supported.")

        try:
            data = await file.read()
        except Exception as exc:  # pragma: no cover - exercised in error handling tests
            raise HTTPException(status_code=400, detail=f"Failed to read upload: {exc}") from exc

        if not data:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        suffix = Path(file.filename or "screenshot").suffix or ".png"
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
