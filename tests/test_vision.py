import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pogo_analyzer import vision


class DummyImage:
    def filter(self, _filter):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyImageModule:
    @staticmethod
    def open(path):  # pragma: no cover - simple stub
        return DummyImage()


class DummyImageOps:
    @staticmethod
    def grayscale(image):  # pragma: no cover - simple stub
        return image

    @staticmethod
    def autocontrast(image):  # pragma: no cover - simple stub
        return image


class DummyImageFilter:
    SHARPEN = object()


class DummyTesseract:
    def __init__(self, text: str):
        self._text = text

    def image_to_string(self, image, config=None):  # pragma: no cover - exercised in tests
        return self._text


def create_sample_screenshot(tmp_path: Path, lines, filename: str) -> Path:
    path = tmp_path / filename
    path.write_text("\n".join(lines))
    return path


def configure_dummy_imaging(monkeypatch):
    monkeypatch.setattr(vision, "Image", DummyImageModule, raising=False)
    monkeypatch.setattr(vision, "ImageOps", DummyImageOps, raising=False)
    monkeypatch.setattr(vision, "ImageFilter", DummyImageFilter, raising=False)


def test_scan_screenshot_extracts_bulbasaur(tmp_path, monkeypatch):
    lines = ["Bulbasaur", "CP 597", "IV 10/11/12"]
    screenshot = create_sample_screenshot(tmp_path, lines, "bulbasaur.png")
    configure_dummy_imaging(monkeypatch)
    monkeypatch.setattr(vision, "pytesseract", DummyTesseract("\n".join(lines)), raising=False)

    result = vision.scan_screenshot(screenshot)

    assert result["name"] == "Bulbasaur"
    assert result["form"] == "Normal"
    assert result["ivs"] == (10, 11, 12)
    assert result["level"] == pytest.approx(20.0)


def test_scan_screenshot_extracts_form(tmp_path, monkeypatch):
    lines = ["Galarian Stunfisk", "CP 1509", "IV 15 / 14 / 15"]
    screenshot = create_sample_screenshot(tmp_path, lines, "stunfisk.png")
    configure_dummy_imaging(monkeypatch)
    monkeypatch.setattr(vision, "pytesseract", DummyTesseract("\n".join(lines)), raising=False)

    result = vision.scan_screenshot(screenshot)

    assert result["name"] == "Stunfisk"
    assert result["form"] == "Galarian"
    assert result["ivs"] == (15, 14, 15)
    assert result["level"] == pytest.approx(24.5)


def test_scan_screenshot_requires_tesseract(tmp_path, monkeypatch):
    lines = ["Bulbasaur", "CP 597", "IV 10/11/12"]
    screenshot = create_sample_screenshot(tmp_path, lines, "missing_engine.png")
    configure_dummy_imaging(monkeypatch)
    monkeypatch.setattr(vision, "pytesseract", None, raising=False)

    with pytest.raises(RuntimeError):
        vision.scan_screenshot(screenshot)

