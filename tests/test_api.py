import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pogo_analyzer import api, vision  # noqa: E402
from pogo_analyzer.errors import ProcessingError  # noqa: E402
from pogo_analyzer.observability import metrics_snapshot  # noqa: E402

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc````\x00\x00\x00\x04\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_scan_endpoint_returns_analysis(monkeypatch):
    analysis = {"name": "Bulbasaur", "form": "Normal", "ivs": (10, 11, 12), "level": 20.0}
    captured_path: Path | None = None

    def fake_scan(path: Path | str):
        nonlocal captured_path
        captured_path = Path(path)
        assert captured_path.exists()
        return analysis

    monkeypatch.setattr(vision, "scan_screenshot", fake_scan)

    app = api.create_app()
    client = TestClient(app)

    response = client.post(
        "/scan",
        files={"file": ("bulbasaur.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 200
    assert response.json() == {**analysis, "ivs": [10, 11, 12]}
    trace_id = response.headers.get("X-Trace-Id")
    assert trace_id
    assert captured_path is not None
    assert not captured_path.exists()


def test_scan_endpoint_rejects_non_image(monkeypatch):
    monkeypatch.setattr(vision, "scan_screenshot", lambda path: {"ok": True})

    app = api.create_app()
    client = TestClient(app)

    response = client.post(
        "/scan",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    body = response.json()["error"]
    assert body["category"] == "input_error"
    assert "Only image uploads" in body["message"]
    assert body["trace_id"] == response.headers["X-Trace-Id"]


def test_scan_endpoint_rejects_large_upload(monkeypatch):
    monkeypatch.setattr(vision, "scan_screenshot", lambda path: {"ok": True})

    app = api.create_app()
    client = TestClient(app)

    oversized = PNG_BYTES + b"0" * (api._MAX_UPLOAD_SIZE + 1)
    response = client.post(
        "/scan",
        files={"file": ("bulky.png", oversized, "image/png")},
    )

    assert response.status_code == 413
    body = response.json()["error"]
    assert body["category"] == "payload_too_large"
    assert "exceeds" in body["message"]
    assert body["trace_id"] == response.headers["X-Trace-Id"]


def test_scan_endpoint_rejects_corrupted_image(monkeypatch):
    monkeypatch.setattr(vision, "scan_screenshot", lambda path: {"ok": True})

    app = api.create_app()
    client = TestClient(app)

    response = client.post(
        "/scan",
        files={"file": ("fake.png", b"not-a-real-image", "image/png")},
    )

    assert response.status_code == 400
    body = response.json()["error"]
    assert body["category"] == "input_error"
    assert "Unsupported" in body["message"]
    assert body["trace_id"] == response.headers["X-Trace-Id"]


def test_scan_endpoint_returns_processing_error_details(monkeypatch):
    def bad_scan(path):
        raise ProcessingError(
            "OCR failed",
            remediation="Provide a clearer screenshot.",
            context={"attempt": 1},
        )

    monkeypatch.setattr(vision, "scan_screenshot", bad_scan)

    app = api.create_app()
    client = TestClient(app)

    response = client.post(
        "/scan",
        files={"file": ("bulbasaur.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["category"] == "processing_error"
    assert body["trace_id"] == response.headers["X-Trace-Id"]
    assert body["context"] == {"attempt": 1}
    assert "Provide a clearer screenshot" in body["remediation"]


def test_scan_endpoint_unexpected_error_is_traceable(monkeypatch):
    def boom(path):
        raise RuntimeError("boom")

    monkeypatch.setattr(vision, "scan_screenshot", boom)

    app = api.create_app()
    client = TestClient(app)

    response = client.post(
        "/scan",
        files={"file": ("bulbasaur.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 500
    body = response.json()["error"]
    assert body["category"] == "internal_error"
    assert "trace_id" in body
    assert body["trace_id"] == response.headers["X-Trace-Id"]


def test_security_headers_present():
    app = api.create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Content-Security-Policy"].startswith("default-src 'none'")
    body = response.json()
    assert "status" in body
    assert "components" in body
    assert "metrics" in body


def test_metrics_endpoint_exposes_counters(monkeypatch):
    analysis = {"name": "Bulbasaur", "form": "Normal", "ivs": (10, 10, 10), "level": 20.0}
    monkeypatch.setattr(vision, "scan_screenshot", lambda path: analysis)

    app = api.create_app()
    client = TestClient(app)

    before = metrics_snapshot()["counters"].get("pogo_analyzer_scan_requests_total", 0.0)
    response = client.post(
        "/scan",
        files={"file": ("bulbasaur.png", PNG_BYTES, "image/png")},
    )
    assert response.status_code == 200
    after_text = client.get("/metrics").text
    assert "pogo_analyzer_scan_requests_total" in after_text
    assert str(int(before) + 1) in after_text
