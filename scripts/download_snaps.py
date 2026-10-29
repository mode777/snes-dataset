#!/usr/bin/env python3
"""Download libretro Named_Snaps (in-game screenshots) into data/snaps/<slug>.png.

Candidate filenames come from the ROM entries already in data/snes_merged.json
(OpenVGDB romFileName values follow No-Intro naming, which is exactly what
libretro's Named_* trees use). Region preference: World > USA > Europe > Japan.

Output: data/snaps/<slug>.png + data/snap_report.json
The snaps are copied into public/ by scripts/build_public.py (which also maps
slugs — run build_public.py first, or at least once, so the reverse index exists).

Usage:
    uv run python scripts/download_snaps.py            # fetch missing only
    uv run python scripts/download_snaps.py --force    # re-fetch everything
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "snaps"

SYSTEM = "Nintendo - Super Nintendo Entertainment System"
BASE = f"https://thumbnails.libretro.com/{SYSTEM.replace(' ', '%20')}/Named_Snaps"

REGION_SCORE = [("world", 0), ("usa", 1), ("europe", 2), ("japan", 3)]


def snap_candidates(game: dict) -> list[str]:
    """No-Intro base names (without extension) for a game, best region first."""
    cands: list[tuple[int, int, str]] = []
    for i, rom in enumerate(game.get("roms", [])):
        name = rom.get("file") or ""
        base = re.sub(r"\.(sfc|smc|fig|swc)$", "", name, flags=re.IGNORECASE)
        if not base:
            continue
        region = rom.get("region", "").lower()
        score = next((s for key, s in REGION_SCORE if key in region), 4)
        cands.append((score, i, base))
    seen: set[str] = set()
    out: list[str] = []
    for _, _, base in sorted(cands):
        if base not in seen:
            seen.add(base)
            out.append(base)
    return out


def fetch_png(url: str, dest: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": "snes-dataset/0.2"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if not data.startswith(b"\x89PNG"):
            return False
        dest.write_bytes(data)
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def listing_names() -> list[str]:
    """All snap base names in the SNES Named_Snaps dir (from the auto-index)."""
    req = urllib.request.Request(f"{BASE}/", headers={"User-Agent": "snes-dataset/0.2"})
    with urllib.request.urlopen(req, timeout=120) as r:
        html = r.read().decode("utf-8", "replace")
    return [urllib.parse.unquote(h)[:-4] for h in re.findall(r'href="([^"]+\.png)"', html)]


def rescue(missing_slugs: list[str], games: list[dict], by_title: dict[str, str],
           workers: int) -> list[str]:
    """Second chance for misses: match against the server's full file listing."""
    if not missing_slugs:
        return []
    from merge_sources import norm_title, numeric_sig  # same rules as the merge

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    names = listing_names()
    print(f"rescue pass: listing has {len(names)} snaps, {len(missing_slugs)} missing games")
    exact = {norm_title(n): n for n in names}
    ls_keys = list(exact)

    jobs: list[tuple[str, str]] = []
    for game in games:
        slug = by_title.get(game["title"])
        if slug not in set(missing_slugs):
            continue
        for base in snap_candidates(game):
            key = norm_title(base)
            if key in exact:
                jobs.append((slug, exact[key]))
                break
            choice = process.extractOne(key, ls_keys, scorer=fuzz.token_sort_ratio,
                                        score_cutoff=90)
            if choice and numeric_sig(key) == numeric_sig(choice[0]):
                jobs.append((slug, exact[choice[0]]))
                break

    def work(job: tuple[str, str]) -> tuple[str, bool]:
        slug, name = job
        url = f"{BASE}/{urllib.parse.quote(name, safe='()')}.png"
        return slug, fetch_png(url, OUT / f"{slug}.png")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        res = dict(ex.map(work, jobs))
    got = [s for s, ok in res.items() if ok]
    print(f"rescued {len(got)}/{len(missing_slugs)}")
    return got


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="re-download existing snaps")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    games = json.loads((DATA / "snes_merged.json").read_text())
    rev_path = ROOT / "public" / "index-reverse.json"
    reverse = json.loads(rev_path.read_text())  # slug -> title (from build_public)
    by_title = {t: s for s, t in reverse.items()}

    OUT.mkdir(exist_ok=True)
    todo: list[tuple[str, list[str]]] = []  # (slug, candidate base names)
    cached = 0
    for game in games:
        slug = by_title.get(game["title"])
        if not slug:
            continue
        dest = OUT / f"{slug}.png"
        if dest.exists() and not args.force:
            cached += 1
            continue
        cands = snap_candidates(game)
        if cands:
            todo.append((slug, cands))

    print(f"{cached} cached, {len(todo)} to fetch "
          f"({len(games) - cached - len(todo)} skipped: no slug or no ROM names)")

    def work(job: tuple[str, list[str]]) -> tuple[str, bool]:
        slug, cands = job
        dest = OUT / f"{slug}.png"
        for base in cands:
            url = f"{BASE}/{urllib.parse.quote(base, safe='()')}.png"
            if fetch_png(url, dest):
                return slug, True
        return slug, False

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = dict(ex.map(work, todo))

    # ---- rescue pass: exact/fuzzy match against the server's own dir listing
    if results:
        missing_now = [s for s, ok in results.items() if not ok]
        rescued = rescue(missing_now, games, by_title, args.workers)
        for slug in rescued:
            results[slug] = True

    missing = sorted(s for s, results_ok in results.items() if not results_ok)
    report = {
        "cached": cached,
        "downloaded": sum(results.values()),
        "missing": len(missing),
        "missing_slugs": missing,
    }
    (DATA / "snap_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != "missing_slugs"}, indent=1))


if __name__ == "__main__":
    main()
