"""Fetch a small reference DPS table with standard library only.

No extra installs. Parses a simple HTML table from a default public page and
writes `benchmarks/reference_external.csv` for use by the consistency scripts.

Usage (from repo root):
  python benchmarks/fetch_reference_simple.py
  # or provide a different table URL
  python benchmarks/fetch_reference_simple.py --url https://pokemon.gameinfo.io/en/tools/dps
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import urllib.request
from pathlib import Path
from typing import Iterable

try:
    # Reuse the same sample list as quick_consistency so rows align
    from benchmarks.quick_consistency import SAMPLES  # type: ignore
except Exception:  # pragma: no cover
    SAMPLES = [
        {"species": "Mewtwo", "fast": "Confusion", "charge": "Psystrike"},
        {"species": "Rayquaza", "fast": "Dragon Tail", "charge": "Outrage"},
        {"species": "Metagross", "fast": "Bullet Punch", "charge": "Meteor Mash"},
    ]


def _fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=20) as resp:  # nosec - public page
        return resp.read().decode("utf-8", errors="replace")


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def _norm(s: str) -> str:
    s = html.unescape(s or "").strip().lower()
    s = s.replace("’", "'")
    s = re.sub(r"\s+", " ", s)
    # Remove variant adjectives for matching
    s = s.replace("(shadow)", "").replace("shadow", "")
    s = s.replace("(mega)", "").replace("mega", "")
    return s.strip()


def _guess_header_idx(header: list[str], targets: Iterable[str]) -> int | None:
    hdr = [_norm(h) for h in header]
    for i, h in enumerate(hdr):
        for t in targets:
            if t in h:
                return i
    return None


def _parse_first_table(html_text: str) -> list[list[str]]:
    # Extract first <table> ... </table> block
    m = re.search(r"<table[^>]*>(.*?)</table>", html_text, flags=re.I | re.S)
    if not m:
        return []
    table_html = m.group(1)
    # Split into rows and cells
    rows: list[list[str]] = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, flags=re.I | re.S):
        cells = re.findall(r"<(?:th|td)[^>]*>(.*?)</(?:th|td)>", tr, flags=re.I | re.S)
        if not cells:
            continue
        cleaned = [html.unescape(_strip_tags(c)).strip() for c in cells]
        if any(cleaned):
            rows.append(cleaned)
    return rows


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    # GameInfo recently moved pages; try the attackers tool first
    p.add_argument("--url", default="https://pokemon.gameinfo.io/en/tools/attackers")
    p.add_argument("--out", type=Path, default=Path("benchmarks/reference_external.csv"))
    return p.parse_args()


def _try_parse(url: str) -> tuple[list[list[str]], str] | None:
    try:
        html_text = _fetch(url)
    except Exception:
        return None
    rows = _parse_first_table(html_text)
    if not rows:
        return None
    return rows, url


def main() -> Path:
    args = parse_args()
    candidate_urls = [
        args.url,
        "https://pogo.gameinfo.io/en/tools/attackers",
        "https://pokemon.gameinfo.io/en/tools/dps",
    ]
    parsed: tuple[list[list[str]], str] | None = None
    for u in candidate_urls:
        parsed = _try_parse(u)
        if parsed is not None:
            break
    if parsed is None:
        sys.stderr.write(
            "Could not parse a reference table. Try passing --url to a page with a simple DPS table.\n"
        )
        return args.out
    rows, source_url = parsed

    header, body = rows[0], rows[1:]
    i_name = _guess_header_idx(header, ["pokemon", "pokémon", "name"]) or 0
    i_fast = _guess_header_idx(header, ["fast", "quick"]) or 1
    i_charge = _guess_header_idx(header, ["charge", "charged"]) or 2
    i_dps = _guess_header_idx(header, ["dps"]) or 3

    # Build a simple index keyed by normalised species name
    by_name: dict[str, tuple[str, str, float]] = {}
    for r in body:
        if len(r) <= max(i_name, i_fast, i_charge, i_dps):
            continue
        try:
            species = r[i_name]
            # Some pages use a single "Best Moves" column; if so, split on '/'
            fast = r[i_fast]
            charge = r[i_charge]
            if "/" in fast and not charge:
                parts = [p.strip() for p in fast.split("/") if p.strip()]
                fast = parts[0] if parts else fast
                charge = parts[1] if len(parts) > 1 else charge
            dps = float((r[i_dps].split() or ["0"])[0])
        except Exception:
            continue
        by_name.setdefault(_norm(species), (fast, charge, dps))

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["species", "fast_move", "charge_move", "reference_dps", "reference_source"])
        for s in SAMPLES:
            key = _norm(s["species"]) 
            row = by_name.get(key)
            if not row:
                continue
            w.writerow([s["species"], row[0], row[1], f"{row[2]:.3f}", source_url])

    print("Saved:", out.resolve())
    return out


if __name__ == "__main__":  # pragma: no cover
    main()
