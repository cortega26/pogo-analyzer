import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pogo_analyzer import api, vision  # noqa: E402

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
    assert response.json()["detail"] == "Only image uploads are supported."


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
    assert "exceeds" in response.json()["detail"]


def test_scan_endpoint_rejects_corrupted_image(monkeypatch):
    monkeypatch.setattr(vision, "scan_screenshot", lambda path: {"ok": True})

    app = api.create_app()
    client = TestClient(app)

    response = client.post(
        "/scan",
        files={"file": ("fake.png", b"not-a-real-image", "image/png")},
    )

    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


def test_security_headers_present():
    app = api.create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Content-Security-Policy"].startswith("default-src 'none'")
