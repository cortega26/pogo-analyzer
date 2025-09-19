"""Fetch reference DPS from a public ranking page (GameInfo-style).

This script is intentionally simple and opt-in. It parses a single HTML table
from a URL you provide (defaults to a common DPS/TDO ranking page) and writes
`benchmarks/reference_external.csv` with columns our consistency scripts expect.

Requirements (only when you run this script):
  pip install beautifulsoup4 lxml

Usage (from repo root):
  python benchmarks/fetch_reference_gameinfo.py \
    --url https://pokemon.gameinfo.io/en/tools/dps \
    --out benchmarks/reference_external.csv

You may need to adjust --url to the exact DPS/TDO ranking page you use.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
import urllib.request
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Iterable

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception as exc:  # noqa: BLE001
    sys.stderr.write(
        "This script requires BeautifulSoup. Install with: pip install beautifulsoup4 lxml\n"
    )
    raise SystemExit(1) from exc

# Reuse the same samples used by quick_consistency so we compare the same rows
try:
    from benchmarks.quick_consistency import SAMPLES  # type: ignore
except Exception:
    # Fallback small set
    SAMPLES = [
        {"species": "Mewtwo", "fast": "Confusion", "charge": "Psystrike"},
        {"species": "Rayquaza", "fast": "Dragon Tail", "charge": "Outrage"},
        {"species": "Metagross", "fast": "Bullet Punch", "charge": "Meteor Mash"},
    ]


def _norm(s: str) -> str:
    import re

    s = unescape(s or "").strip().lower()
    s = s.replace("’", "'")
    s = re.sub(r"\s+", " ", s)
    s = s.replace("(shadow)", "").replace("shadow", "").replace("(mega)", "").replace("mega", "")
    return s.strip()


@dataclass(frozen=True)
class RefRow:
    species: str
    fast_move: str
    charge_move: str
    dps: float
    source: str


def _fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=20) as resp:  # nosec - user-provided URL
        return resp.read().decode("utf-8", errors="replace")


def _extract_rows(html: str) -> list[list[str]]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = [unescape(td.get_text(" ", strip=True)) for td in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    return rows


def _guess_header_idx(header: list[str], targets: Iterable[str]) -> int | None:
    hdr = [_norm(h) for h in header]
    for i, h in enumerate(hdr):
        for t in targets:
            if t in h:
                return i
    return None


def _parse(url: str) -> list[RefRow]:
    html = _fetch(url)
    rows = _extract_rows(html)
    if not rows:
        return []
    header = rows[0]
    body = rows[1:]
    i_name = _guess_header_idx(header, ["pokemon", "pokémon", "name"]) or 0
    i_fast = _guess_header_idx(header, ["fast", "quick"]) or 1
    i_charge = _guess_header_idx(header, ["charge", "charged"]) or 2
    i_dps = _guess_header_idx(header, ["dps"]) or 3

    out: list[RefRow] = []
    for r in body:
        if len(r) <= max(i_name, i_fast, i_charge, i_dps):
            continue
        species = r[i_name]
        fast = r[i_fast]
        charge = r[i_charge]
        dps_txt = r[i_dps].split()[0]
        try:
            dps = float(dps_txt)
        except Exception:
            continue
        out.append(RefRow(species=species, fast_move=fast, charge_move=charge, dps=dps, source=url))
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="https://pokemon.gameinfo.io/en/tools/dps", help="Reference table URL (GameInfo-style)")
    p.add_argument("--out", type=Path, default=Path("benchmarks/reference_external.csv"))
    return p.parse_args()


def main() -> Path:
    args = parse_args()
    fetched = _parse(args.url)
    if not fetched:
        print("No rows parsed from:", args.url)
        return args.out

    # Build a quick index by normalised species name for lookups
    by_name = {}
    for row in fetched:
        key = _norm(row.species)
        by_name.setdefault(key, []).append(row)

    def pick(species: str) -> RefRow | None:
        key = _norm(species)
        cand = by_name.get(key)
        if not cand:
            return None
        # Pick the first entry; pages usually list best fast/charge per species
        return cand[0]

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["species", "fast_move", "charge_move", "reference_dps", "reference_source"])
        for s in SAMPLES:
            ref = pick(s["species"])
            if ref is None:
                continue
            w.writerow([s["species"], ref.fast_move, ref.charge_move, f"{ref.dps:.3f}", args.url])

    print("Saved:", out.resolve())
    return out


if __name__ == "__main__":  # pragma: no cover
    main()

