import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pogo_analyzer import api, vision  # noqa: E402


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
        files={"file": ("bulbasaur.png", b"pretend-bytes", "image/png")},
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
