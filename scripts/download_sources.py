#!/usr/bin/env python3
"""Download the SNES data sources into data/.

Idempotent: skips files that already exist (pass --force to re-download).

Usage:
    uv run python scripts/download_sources.py             # metadata only (~15 MB)
    uv run python scripts/download_sources.py --images    # + 232 MB box art set
"""

from __future__ import annotations

import argparse
import urllib.request
import zipfile
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

SOURCES = {
    # thedevastator bundle: df_1..df_5.csv (Wikipedia scrape) + snes.csv (sergenkaraoglan)
    "kaggle_thedevastator.zip": "https://www.kaggle.com/api/v1/datasets/download/thedevastator/snes-games-a-comprehensive-list-of-games",
    # OpenVGDB SQLite (all platforms, we filter SNES)
    "openvgdb.zip": "https://github.com/OpenVGDB/OpenVGDB/releases/download/v29.0/openvgdb.zip",
    # karlforshaw/opengamedb: scores + cover URLs
    "opengamedb_snes.csv": "https://raw.githubusercontent.com/karlforshaw/opengamedb/master/super_nintendo_entertainment_system.csv",
    # sergenkaraoglan box art (separate dataset, 232 MB)
    "kaggle_snes_boxart.zip": "https://www.kaggle.com/api/v1/datasets/download/sergenkaraoglan/super-nintendo-entertainment-system-box-art",
}

WANT_IMAGES = ["kaggle_snes_boxart.zip"]


def fetch(name: str, url: str, force: bool = False) -> Path | None:
    dest = DATA / name
    if dest.exists() and not force:
        print(f"  = {name} (cached)")
        return dest
    print(f"  ↓ {name} ...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "snes-dataset/0.1"})
    with urllib.request.urlopen(req, timeout=300) as r, dest.open("wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    print(f"    {dest.stat().st_size // 1024} KB")
    return dest


def unzip(archive: Path, members: list[str] | None = None) -> None:
    with zipfile.ZipFile(archive) as z:
        for member in members or z.namelist():
            target = DATA / Path(member).name
            if target.exists():
                continue
            with z.open(member) as src, target.open("wb") as out:
                out.write(src.read())
            print(f"  → {target.name}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--images", action="store_true", help="also download the 232 MB box art set")
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    args = ap.parse_args()

    DATA.mkdir(exist_ok=True)
    wanted = SOURCES if args.images else {k: v for k, v in SOURCES.items() if k not in WANT_IMAGES}

    for name, url in wanted.items():
        archive = fetch(name, url, args.force)
        if archive is None:
            continue
        if archive.suffix == ".zip":
            if archive.name == "kaggle_snes_boxart.zip":
                unzip(archive)  # keep folder structure: game_covers_SNES[-large]/...
            else:
                unzip(archive)  # flat CSVs / sqlite
        print()

    print("done. files in data/:")
    for p in sorted(DATA.iterdir()):
        if p.is_file():
            print(f"  {p.name} ({p.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
