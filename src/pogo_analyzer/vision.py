"""Lightweight OCR pipeline for Pokémon GO screenshots."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:  # pragma: no cover - optional dependency
    from PIL import Image, ImageFilter, ImageOps  # type: ignore
except Exception:  # pragma: no cover - gracefully handled at runtime
    Image = None  # type: ignore
    ImageFilter = None  # type: ignore
    ImageOps = None  # type: ignore

from . import calculations, data_loader

try:  # pragma: no cover - exercised via tests when pytesseract is available
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover - gracefully handled at runtime
    pytesseract = None  # type: ignore

_STATS_CACHE: Optional[Dict[str, Dict[str, data_loader.PokemonSpecies]]] = None
_SPECIES_INDEX: Optional[Dict[str, str]] = None
_FORM_INDEX: Optional[Dict[str, str]] = None

CP_PATTERN = re.compile(r"CP\s*[:#-]?\s*(\d+)", re.IGNORECASE)
IV_PATTERN = re.compile(
    r"IVS?\s*[:#-]?\s*(\d{1,2})\s*[\/|]\s*(\d{1,2})\s*[\/|]\s*(\d{1,2})",
    re.IGNORECASE,
)
LEVEL_PATTERN = re.compile(r"(?:LV|LEVEL)\s*[:#-]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _load_caches() -> None:
    global _STATS_CACHE, _SPECIES_INDEX, _FORM_INDEX
    if _STATS_CACHE is not None:
        return
    stats = data_loader.load_pokemon_stats()
    _STATS_CACHE = stats
    _SPECIES_INDEX = {_normalise(name): name for name in stats}
    form_index: Dict[str, str] = {}
    for forms in stats.values():
        for form_name in forms:
            form_index.setdefault(_normalise(form_name), form_name)
    _FORM_INDEX = form_index


def _get_species_entry(name: str, form: str) -> data_loader.PokemonSpecies:
    _load_caches()
    assert _STATS_CACHE is not None
    species_forms = _STATS_CACHE.get(name)
    if not species_forms:
        raise ValueError(f"Unknown Pokémon species: {name}")
    if form in species_forms:
        return species_forms[form]
    if form != "Normal" and "Normal" in species_forms:
        return species_forms["Normal"]
    available = ", ".join(sorted(species_forms))
    raise ValueError(f"Form '{form}' not available for {name}. Available: {available}")


def _clean_line(line: str) -> str:
    return re.sub(r"[^0-9A-Za-z()' -]", "", line).strip()


def _extract_text_lines(image: Image.Image) -> List[str]:
    if ImageOps is None or ImageFilter is None:
        raise RuntimeError("Pillow is required to process screenshots.")
    if pytesseract is None:  # pragma: no cover - behaviour tested explicitly
        raise RuntimeError(
            "pytesseract is required to scan screenshots. Install Tesseract OCR first."
        )
    grayscale = ImageOps.grayscale(image)
    contrasted = ImageOps.autocontrast(grayscale)
    sharpened = contrasted.filter(ImageFilter.SHARPEN)
    text = pytesseract.image_to_string(sharpened, config="--psm 6")
    return [line.strip() for line in text.splitlines() if line.strip()]


def _match_species(candidate: str) -> Optional[str]:
    _load_caches()
    assert _SPECIES_INDEX is not None
    normalised = _normalise(candidate)
    if normalised in _SPECIES_INDEX:
        return _SPECIES_INDEX[normalised]
    tokens = candidate.split()
    for length in range(len(tokens), 0, -1):
        normalised = _normalise(" ".join(tokens[:length]))
        if normalised in _SPECIES_INDEX:
            return _SPECIES_INDEX[normalised]
    return None


def _match_form(candidate: str, species: str) -> str:
    _load_caches()
    assert _STATS_CACHE is not None and _FORM_INDEX is not None
    normalised = _normalise(candidate)
    form = _FORM_INDEX.get(normalised)
    if form and form in _STATS_CACHE[species]:
        return form
    return "Normal"


def _extract_name_and_form(lines: Iterable[str]) -> Tuple[str, str]:
    for raw_line in lines:
        cleaned = _clean_line(raw_line)
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered.startswith("cp") or lowered.startswith("iv"):
            continue
        match = re.match(r"(.+?)\(([^)]+)\)$", cleaned)
        if match:
            candidate_name = match.group(1).strip()
            candidate_form = match.group(2).strip()
            species = _match_species(candidate_name)
            if species:
                return species, _match_form(candidate_form, species)
        species = _match_species(cleaned)
        tokens = cleaned.split()
        if species:
            if len(tokens) > 1:
                possible_form = tokens[0]
                remaining = " ".join(tokens[1:])
                confirmed_species = _match_species(remaining)
                if confirmed_species == species:
                    form = _match_form(possible_form, species)
                    if form != "Normal" or possible_form.lower() != "cp":
                        return species, form
            return species, "Normal"
        if len(tokens) > 1:
            possible_form = tokens[0]
            remaining = " ".join(tokens[1:])
            species = _match_species(remaining)
            if species:
                form = _match_form(possible_form, species)
                if form != "Normal" or possible_form.lower() != "cp":
                    return species, form
                return species, "Normal"
    raise ValueError("Unable to determine Pokémon name from screenshot text")


def _extract_cp(lines: Iterable[str]) -> int:
    for line in lines:
        match = CP_PATTERN.search(line)
        if match:
            return int(match.group(1))
    raise ValueError("Unable to determine CP from screenshot text")


def _extract_ivs(lines: Iterable[str]) -> Tuple[int, int, int]:
    for line in lines:
        match = IV_PATTERN.search(line)
        if match:
            return tuple(int(match.group(i)) for i in range(1, 4))  # type: ignore[return-value]
    raise ValueError("Unable to determine IVs from screenshot text")


def _extract_level(lines: Iterable[str]) -> Optional[float]:
    for line in lines:
        match = LEVEL_PATTERN.search(line)
        if match:
            return float(match.group(1))
    return None


def _infer_level(name: str, form: str, ivs: Tuple[int, int, int], cp: int) -> float:
    species = _get_species_entry(name, form)
    multipliers = data_loader.load_cp_multipliers()
    candidate_levels = sorted(level for level in multipliers if 1.0 <= level <= 55.0)
    best_level = None
    best_delta = float("inf")
    for level in candidate_levels:
        stats = calculations.compute_stats(species, ivs, level)
        expected_cp = calculations.calc_cp(stats, level)
        delta = abs(expected_cp - cp)
        if delta < best_delta:
            best_delta = delta
            best_level = level
            if delta == 0:
                break
    if best_level is None or best_delta > 5:
        raise ValueError(
            f"Unable to infer level for {name} {form} with CP {cp} and IVs {ivs}"
        )
    return float(best_level)


def scan_screenshot(path: Path | str) -> Dict[str, object]:
    """Return Pokémon metadata extracted from a game screenshot.

    Parameters
    ----------
    path:
        Filesystem path to a screenshot image that contains Pokémon detail text.

    Returns
    -------
    Dict[str, object]
        Dictionary containing ``name``, ``form``, ``ivs`` (attack, defence, stamina),
        and ``level`` derived from the recognised text.
    """

    if Image is None:
        raise RuntimeError("Pillow is required to open screenshots.")

    image_path = Path(path)
    if not image_path.exists():
        raise FileNotFoundError(f"Screenshot not found: {path}")

    with Image.open(image_path) as raw_image:
        lines = _extract_text_lines(raw_image)

    if not lines:
        raise ValueError("OCR returned no usable text")

    name, form = _extract_name_and_form(lines)
    cp = _extract_cp(lines)
    ivs = _extract_ivs(lines)
    level = _extract_level(lines)
    if level is None:
        level = _infer_level(name, form, ivs, cp)

    return {"name": name, "form": form, "ivs": ivs, "level": level}


__all__ = ["scan_screenshot"]

