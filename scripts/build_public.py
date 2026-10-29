#!/usr/bin/env python3
"""Build the public/ static dataset (intended for GitHub Pages).

Reads data/snes_merged.json and produces:
  public/index.json                  { "<slug>": "<Original Title>", ... }
  public/catalog.json                [{slug,title,year,developer,...}] for the UI grid
  public/<slug>/data.json            full metadata; images referenced by filename
  public/<slug>/thumb.<ext>          box art thumbnail (Kaggle "small" set) if available
  public/<slug>/box.<ext>            full box image (Kaggle "large" set) if available
  public/.nojekyll                   keep GH Pages from Jekyll-processing 3k files

public/index.html (the committed browser shell) is preserved, not regenerated.

Usage:
    uv run python scripts/build_public.py
"""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PUBLIC = ROOT / "public"

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    t = unicodedata.normalize("NFKD", title)
    t = "".join(c for c in t if not unicodedata.combining(c)).casefold()
    slug = _SLUG_STRIP.sub("-", t).strip("-")
    return slug or "game"


def unique_slug(slug: str, used: set[str]) -> str:
    if slug not in used:
        return slug
    n = 2
    while f"{slug}-{n}" in used:
        n += 1
    return f"{slug}-{n}"


def main() -> None:
    games = json.loads((DATA / "snes_merged.json").read_text())

    # regenerate everything except committed static shell files (index.html)
    for entry in PUBLIC.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
        elif entry.name in ("index.json", "catalog.json"):
            entry.unlink()
    PUBLIC.mkdir(exist_ok=True)
    (PUBLIC / ".nojekyll").touch()

    index: dict[str, str] = {}
    catalog: list[dict] = []
    used: set[str] = set()
    with_thumb = with_box = 0

    for game in sorted(games, key=lambda g: (g["title"] or "").casefold()):
        title = game["title"]
        slug = unique_slug(slugify(title), used)
        used.add(slug)
        index[slug] = title

        game_dir = PUBLIC / slug
        game_dir.mkdir()

        data = {k: v for k, v in game.items() if k not in ("box_art_small", "box_art_large")}
        images: dict[str, str] = {}

        if small := game.get("box_art_small"):
            src = ROOT / small
            if src.exists():
                dest = f"thumb{src.suffix.lower()}"
                shutil.copy2(src, game_dir / dest)
                images["thumb"] = dest
                with_thumb += 1
        if large := game.get("box_art_large"):
            src = ROOT / large
            if src.exists():
                dest = f"box{src.suffix.lower()}"
                shutil.copy2(src, game_dir / dest)
                images["box"] = dest
                with_box += 1
        if images:
            data["images"] = images

        (game_dir / "data.json").write_text(
            json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8"
        )
        catalog.append({
            "slug": slug,
            "title": title,
            "year": data.get("year"),
            "developer": next(iter(data.get("developer") or []), None),
            "publisher": next(iter(data.get("publisher") or []), None),
            "genre": ", ".join(data.get("genre") or []),
            "thumb": "thumb" in images,
        })

    (PUBLIC / "index.json").write_text(
        json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    (PUBLIC / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False), encoding="utf-8"
    )

    size = sum(f.stat().st_size for f in PUBLIC.rglob("*") if f.is_file())
    print(f"games: {len(index)}  (thumb: {with_thumb}, box: {with_box})")
    print(f"public/ size: {size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
