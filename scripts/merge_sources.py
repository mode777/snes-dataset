#!/usr/bin/env python3
"""Merge the SNES sources in data/ into one comprehensive dataset.

Sources (see docs/data-sources.md):
  - snes.csv            (Kaggle/sergenkaraoglan, CC0): dev/pub/year/players/tags/description
  - df_1.csv, df_2.csv, df_3.csv (Kaggle/thedevastator): Wikipedia scrape, per-region dates
  - opengamedb_snes.csv (GitHub/karlforshaw): GameFAQs+Metacritic scores, cover URLs
  - openvgdb.sqlite     (OpenVGDB v29): covers, descriptions, genres, dates
  - game_covers_SNES-small|large/ (Kaggle/sergenkaraoglan): box art joined by title

Records are keyed by normalized exact title; leftover single-source records are
fuzzy-linked into multi-source records (rapidfuzz token_sort_ratio).

Output: data/snes_merged.json + data/merge_report.json

Usage:
    uv run python scripts/merge_sources.py [--min-score 93]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# ---------------------------------------------------------------- helpers


def norm_title(t: str) -> str:
    """Normalize a game title into a merge key."""
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.casefold().replace("’", "'")
    t = re.sub(r"[^a-z0-9']+", " ", t)
    return re.sub(r"\s+", " ", t).strip().strip("'")


def year_of(date_str: str) -> int | None:
    m = re.search(r"(?:19|20)\d{2}", date_str or "")
    return int(m.group(0)) if m else None


def add_unique(lst: list, value) -> None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return
    v = value.strip() if isinstance(value, str) else value
    if not any((v.casefold() if isinstance(v, str) else v)
               == (x.casefold() if isinstance(x, str) else x) for x in lst):
        lst.append(v)


class Record:
    """Mutable merge target; list fields keep insertion (source-priority) order."""

    def __init__(self, key: str, title: str):
        self.key = key
        self.titles: list[str] = []
        self.developer: list[str] = []
        self.publisher: list[str] = []
        self.genre: list[str] = []
        self.tags: list[str] = []
        self.release_dates: dict[str, str] = {}
        self.years: set[int] = set()
        self.descriptions: dict[str, str] = {}  # source name -> text
        self.players: str | None = None
        self.languages: list[str] = []
        self.roms: list[dict] = []  # {crc32, md5, sha1, region, file} from OpenVGDB
        self.gf_score: float | None = None
        self.metascore: int | None = None
        self.cover_urls: list[str] = []
        self.box_art_small: str | None = None
        self.box_art_large: str | None = None
        self.sources: list[str] = []
        self.see_title(title)

    def see_title(self, title: str) -> None:
        add_unique(self.titles, title)

    def touch(self, source: str) -> None:
        add_unique(self.sources, source)

    def to_json(self) -> dict:
        desc_source = next(
            (s for s in ["snes_csv", "opengamedb", "openvgdb"] if s in self.descriptions), None
        )
        return {
            "title": self.titles[0],
            "aliases": self.titles[1:],
            "year": min(self.years) if self.years else None,
            "release_dates": self.release_dates,
            "developer": self.developer,
            "publisher": self.publisher,
            "genre": self.genre,
            "tags": self.tags,
            "description": self.descriptions.get(desc_source) if desc_source else None,
            "description_source": desc_source,
            "players": self.players,
            "languages": self.languages,
            "roms": self.roms,
            "gf_score": self.gf_score,
            "metascore": self.metascore,
            "cover_urls": self.cover_urls,
            "box_art_small": self.box_art_small,
            "box_art_large": self.box_art_large,
            "sources": self.sources,
        }


def merge_into(records: dict[str, Record], key: str, source: str, **f) -> Record:
    rec = records.get(key)
    if rec is None:
        rec = records[key] = Record(key, f["title"])
    rec.touch(source)
    rec.see_title(f["title"])
    for d in f.get("developer", []):
        add_unique(rec.developer, d)
    for p in f.get("publisher", []):
        add_unique(rec.publisher, p)
    for g in f.get("genre", []):
        add_unique(rec.genre, g)
    for t in f.get("tags", []):
        add_unique(rec.tags, t)
    rec.release_dates.update(f.get("release_dates", {}))
    rec.years.update(y for y in f.get("years", []) if y)
    if (d := f.get("description")) and d.strip():
        rec.descriptions.setdefault(source, d.strip())
    rec.players = rec.players or f.get("players")
    for lang in f.get("languages", []):
        add_unique(rec.languages, lang)
    for rom in f.get("roms", []):
        if not any(r["crc32"] == rom["crc32"] for r in rec.roms):
            rec.roms.append(rom)
    if f.get("gf_score") is not None:
        rec.gf_score = f["gf_score"]
    if f.get("metascore") is not None:
        rec.metascore = f["metascore"]
    for url in f.get("cover_urls", []):
        add_unique(rec.cover_urls, url)
    rec.box_art_small = rec.box_art_small or f.get("box_art_small")
    rec.box_art_large = rec.box_art_large or f.get("box_art_large")
    return rec


# ---------------------------------------------------------------- loaders


def load_snes_csv(records: dict[str, Record]) -> int:
    with (DATA / "snes.csv").open(newline="", encoding="utf-8", errors="replace") as fh:
        n = 0
        for row in csv.DictReader(fh):
            title = (row.get("Title") or "").strip()
            if not title:
                continue
            n += 1
            merge_into(
                records, norm_title(title), "snes_csv",
                title=title,
                developer=[row.get("Developer") or ""],
                publisher=[row.get("Publisher") or ""],
                tags=[t.strip() for t in (row.get("Tags") or "").split(",") if t.strip()],
                years=[year_of(row.get("Year") or "")],
                description=row.get("Description") or "",
                players=(row.get("Players") or "").strip() or None,
                languages=[row.get("Languages") or ""],
            )
    return n


def load_wikipedia(records: dict[str, Record]) -> int:
    """df_1.csv: duplicate 'Release date' headers -> read by column index.
    Indexes: 1 title, 2 developer, 3 publisher, 4 JP, 5 NA, 6 PAL."""
    with (DATA / "df_1.csv").open(newline="", encoding="utf-8", errors="replace") as fh:
        rows = list(csv.reader(fh))
    n = 0
    for row in rows[2:]:  # row 0 = header, row 1 = region subheader
        if len(row) < 7:
            continue
        title = row[1].strip()
        if not title or title == "Title":
            continue
        n += 1
        dates = {
            region: row[idx].strip()
            for idx, region in [(4, "japan"), (5, "north_america"), (6, "pal")]
            if row[idx].strip() and row[idx].strip().lower() != "unreleased"
        }
        merge_into(
            records, norm_title(title), "wikipedia",
            title=title,
            developer=[row[2]],
            publisher=[row[3]],
            release_dates=dates,
            years=[year_of(" ".join(dates.values()))],
        )
    return n


def load_df2(records: dict[str, Record]) -> int:
    with (DATA / "df_2.csv").open(newline="", encoding="utf-8", errors="replace") as fh:
        n = 0
        for row in csv.DictReader(fh):
            title = (row.get("Title") or "").strip()
            if not title:
                continue
            n += 1
            date = (row.get("Release date") or "").strip()
            merge_into(
                records, norm_title(title), "wikipedia_special",
                title=title,
                developer=[row.get("Developer(s)") or ""],
                publisher=[row.get("Publisher(s)") or ""],
                release_dates={"other": date} if date.lower() != "unreleased" else {},
                years=[year_of(date)],
            )
    return n


def load_df3(records: dict[str, Record]) -> int:
    region_map = {"jp": "japan", "na": "north_america", "pal": "pal"}
    with (DATA / "df_3.csv").open(newline="", encoding="utf-8", errors="replace") as fh:
        n = 0
        for row in csv.DictReader(fh):
            title = (row.get("Title(s)") or "").strip()
            if not title:
                continue
            n += 1
            date = (row.get("Release date") or "").strip()
            regions = [
                region_map[p.strip().casefold()]
                for p in (row.get("Regions released") or "").split(",")
                if p.strip().casefold() in region_map
            ]
            merge_into(
                records, norm_title(title), "wikipedia_unlicensed",
                title=title,
                developer=[row.get("Developer") or ""],
                publisher=[row.get("Publisher") or ""],
                release_dates={r: date for r in regions} if date.lower() != "unreleased" else {},
                years=[year_of(date)],
            )
    return n


def load_opengamedb(records: dict[str, Record]) -> int:
    with (DATA / "opengamedb_snes.csv").open(
        newline="", encoding="utf-8", errors="replace"
    ) as fh:
        n = 0
        for row in csv.DictReader(fh):
            title = (row.get("title") or "").strip()
            if not title:
                continue
            n += 1
            gf, meta = row.get("gf_score") or "", row.get("metascore") or ""
            released = row.get("released") or ""
            merge_into(
                records, norm_title(title), "opengamedb",
                title=title,
                genre=[row.get("genre") or ""],
                release_dates={"first_release": released} if released else {},
                years=[year_of(released)],
                description=row.get("description") or "",
                gf_score=float(gf) if gf.replace(".", "").isdigit() else None,
                metascore=int(meta) if meta.isdigit() else None,
                cover_urls=[row.get("cover_art_url") or ""],
            )
    return n


def load_openvgdb(records: dict[str, Record]) -> int:
    conn = sqlite3.connect(DATA / "openvgdb.sqlite")
    cur = conn.cursor()
    cols = {r[1] for r in cur.execute("PRAGMA table_info(RELEASES)")}
    region_expr = "TEMPregionLocalizedName" if "TEMPregionLocalizedName" in cols else "''"
    # JOIN ROMs for checksums (No-Intro style, headerless, uppercase hex)
    query = (
        "SELECT rel.releaseTitleName, rel.releaseDate, rel.releaseDeveloper, "
        "rel.releasePublisher, rel.releaseGenre, rel.releaseDescription, "
        "rel.releaseCoverFront, rel.releaseCoverBack, rel.releaseCoverCart, "
        f"{region_expr}, r.romHashCRC, r.romHashMD5, r.romHashSHA1, "
        "COALESCE(r.TEMPromRegion, ''), r.romFileName "
        "FROM RELEASES rel LEFT JOIN ROMs r ON r.romID = rel.romID "
        "WHERE rel.TEMPsystemShortName='SNES'"
    )
    n = 0
    for (title, date, dev, pub, genre, desc, cf, cb, cc, region,
         crc, md5, sha1, rom_region, rom_file) in cur.execute(query):
        title = (title or "").strip()
        if not title:
            continue
        n += 1
        region_key = re.sub(r"\s+", "_", (region or "unknown").strip().lower())
        dates = {region_key: date} if date and date.lower() != "unreleased" else {}
        rom = None
        if crc:
            rom = {
                "crc32": crc.strip().upper(),
                "md5": (md5 or "").strip().upper(),
                "sha1": (sha1 or "").strip().upper(),
                "region": rom_region.strip(),
                "file": (rom_file or "").strip(),
            }
        merge_into(
            records, norm_title(title), "openvgdb",
            title=title,
            developer=[dev or ""],
            publisher=[pub or ""],
            genre=[g.strip() for g in (genre or "").split(",") if g.strip()],
            release_dates=dates,
            years=[year_of(date or "")],
            description=desc or "",
            cover_urls=[c for c in [cf, cb, cc] if c],
            roms=[rom] if rom else [],
        )
    conn.close()
    return n


def load_boxart() -> tuple[dict[str, str], dict[str, str]]:
    """Map normalized title -> repo-relative path for both box art sets."""
    small: dict[str, str] = {}
    large: dict[str, str] = {}
    folders = [
        (DATA / "game_covers_SNES-small" / "game_covers_SNES", small),
        (DATA / "game_covers_SNES_large" / "game_covers_SNES_large", large),
    ]
    for d, target in folders:
        if not d.is_dir():
            continue
        for f in d.iterdir():
            stem = f.stem.removeprefix("Cover for ").strip().rstrip(".")
            target[norm_title(stem)] = str(f.relative_to(ROOT))
    return small, large


# ---------------------------------------------------------------- fuzzy linking

ROMAN_TO_INT = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8,
    "ix": 9, "x": 10, "xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15,
}

_SIG_STOPWORDS = {"a", "an", "the", "of", "in", "n"}  # single-letter words to ignore


def numeric_sig(key: str) -> frozenset[str]:
    """Signature of 'number words' in a title: digits, roman numerals, X2-style
    suffixes, and standalone letters (RR-Z vs RR). Sequels and letter-variants
    must never be fuzzy-merged, so signatures must match."""
    nums = set(re.findall(r"\d+", key))
    for tok in key.split():
        if tok in ROMAN_TO_INT:
            nums.add(str(ROMAN_TO_INT[tok]))  # "II" ~ "2"
        elif re.fullmatch(r"[ivx]+\d+|\d+[ivx]+", tok):
            nums.add(tok)  # opaque "x2"-style suffix
        elif len(tok) == 1 and tok.isalpha() and tok not in _SIG_STOPWORDS:
            nums.add(tok)  # trailing letters: "... RR-Z" -> "z"
    return frozenset(nums)


def absorb(target: Record, src: Record) -> None:
    """Fold a single-source record into its merge target."""
    merge_into(
        {target.key: target}, target.key, src.sources[0] if src.sources else "fuzzy",
        title=src.titles[0],
        developer=src.developer,
        publisher=src.publisher,
        genre=src.genre,
        release_dates=src.release_dates,
        years=list(src.years),
        gf_score=src.gf_score,
        metascore=src.metascore,
        cover_urls=src.cover_urls,
        box_art_small=src.box_art_small,
        box_art_large=src.box_art_large,
    )
    for s, d in src.descriptions.items():
        target.descriptions.setdefault(s, d)
    for s in src.sources:
        target.touch(s)
    for t in src.titles:
        add_unique(target.titles, t)
    for t in src.tags:
        add_unique(target.tags, t)
    for lang in src.languages:
        add_unique(target.languages, lang)
    target.players = target.players or src.players


def fuzzy_link(records: dict[str, Record], min_score: float) -> list[dict]:
    """Keep multi-source records as-is; fuzzy-link single-source stragglers.

    token_sort_ratio, not token_set_ratio: the latter scores 100 for pure
    subsets and would merge "Super Mario World" into "Super Mario World 2".
    """
    order = sorted(records, key=lambda k: (-len(records[k].sources), k))
    result: dict[str, Record] = {}
    merges: list[dict] = []
    for key in order:
        rec = records[key]
        if len(rec.sources) > 1 or not result:
            result[key] = rec
            continue
        choice = process.extractOne(
            key, list(result), scorer=fuzz.token_sort_ratio, score_cutoff=min_score
        )
        if choice is None:
            result[key] = rec
            continue
        best_key, score, _ = choice
        if numeric_sig(key) != numeric_sig(best_key):
            # e.g. "Hokuto no Ken 6" vs "Hokuto no Ken 5": similar text, different games
            result[key] = rec
            continue
        target = result[best_key]
        absorb(target, rec)
        merges.append({"merged": rec.titles[0], "into": target.titles[0],
                       "score": round(score, 1)})
    records.clear()
    records.update(result)
    return merges


# ---------------------------------------------------------------- main


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-score", type=float, default=93.0,
                    help="rapidfuzz cutoff for fuzzy title merges (default: 93)")
    args = ap.parse_args()

    records: dict[str, Record] = {}
    counts: dict[str, int] = {}
    for name, loader in [
        ("snes_csv", load_snes_csv),
        ("wikipedia", load_wikipedia),
        ("wikipedia_special", load_df2),
        ("wikipedia_unlicensed", load_df3),
        ("opengamedb", load_opengamedb),
        ("openvgdb", load_openvgdb),
    ]:
        counts[name] = loader(records)
        print(f"  {name}: {counts[name]} rows")

    small_idx, large_idx = load_boxart()
    print(f"  box art index: small={len(small_idx)}, large={len(large_idx)}")
    for rec in records.values():
        rec.box_art_small = small_idx.get(rec.key)
        rec.box_art_large = large_idx.get(rec.key)

    pre = len(records)
    merges = fuzzy_link(records, args.min_score)
    print(f"  groups: {pre} exact -> {len(records)} after {len(merges)} fuzzy merges")

    out = sorted(
        (r.to_json() for r in records.values()),
        key=lambda r: (r["title"] or "").casefold(),
    )
    (DATA / "snes_merged.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))

    coverage = {
        field: (n := sum(1 for r in out if r.get(field)),
                f"{n} ({100 * n // len(out)}%)")[1]
        for field in ["year", "release_dates", "developer", "publisher", "genre",
                      "description", "box_art_small", "gf_score", "metascore",
                      "cover_urls"]
    }
    report = {
        "rows_loaded": counts,
        "records_out": len(out),
        "multi_source_records": sum(1 for r in out if len(r["sources"]) > 1),
        "fuzzy_merges": len(merges),
        "fuzzy_merge_list": merges,
        "coverage": coverage,
    }
    (DATA / "merge_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in report.items() if k != "fuzzy_merge_list"}, indent=1))


if __name__ == "__main__":
    main()
