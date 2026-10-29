# SNES Dataset — static "API"

A free, static JSON dataset of **3,070 Super Nintendo (SNES) games**: metadata,
per-region release dates, and box art. No auth, no rate limits — it's just
files on a CDN (GitHub Pages), so standard HTTP caching applies.

**Base URL:** `https://mode777.github.io/snes-dataset/`

## Endpoints (files)

| Path | Description |
|---|---|
| `/index.json` | `{ "<Original Title>": "<slug>" }` — game title → folder/slug |
| `/index-reverse.json` | `{ "<slug>": "<Original Title>" }` — the reverse mapping |
| `/catalog.json` | Array of lightweight records (one per game) — powers the grid UI |
| `/by-crc.json` | `{ "<CRC32>": "<slug>" }` — exact ROM-identity lookup (see below) |
| `/<slug>/data.json` | Full metadata for one game |
| `/<slug>/thumb.png` | Box art thumbnail, 140×186 PNG (1,645 games) |
| `/<slug>/box.jpeg` | Full box image (1,645 games) |
| `/` | This dataset, browsable (`index.html`) |

- **Slug rules:** lowercase kebab-case, accents folded, all non-`[a-z0-9]` dropped.
  `Chrono Trigger` → `chrono-trigger`, `3×3 Eyes…` → `3-3-eyes-seima-kourin-den`.
  Rare collisions get a numeric suffix (`-2`, `-3`); `index-reverse.json` is
  authoritative in the slug → title direction.
- `images` inside `data.json` references **filenames relative to the same folder**.

## Usage

```sh
# resolve a known game name to its folder
curl -s .../index.json | jq '."Chrono Trigger"'                        # "chrono-trigger"

# resolve a folder/slug back to the display title
curl -s .../index-reverse.json | jq '."chrono-trigger"'                # "Chrono Trigger"

# exact lookup by ROM checksum — no fuzzy matching needed
curl -s .../by-crc.json | jq '."E95A3DD7"'                             # "2020-super-baseball"

# one full record + its thumbnail
curl -sO .../chrono-trigger/data.json
curl -so thumb.png .../chrono-trigger/thumb.png
```

```js
// walk the whole dataset
const catalog = await (await fetch("/snes-dataset/catalog.json")).json();
for (const { slug } of catalog) {
  const game = await (await fetch(`/snes-dataset/${slug}/data.json`)).json();
  // ...
}
// or start from a display title
const slugs = await (await fetch("/snes-dataset/index.json")).json();
const slug = slugs["Chrono Trigger"];
```

```python
import requests, time

base = "https://mode777.github.io/snes-dataset"
catalog = requests.get(f"{base}/catalog.json", timeout=30).json()
for g in catalog:
    game = requests.get(f"{base}/{g['slug']}/data.json", timeout=30).json()
    ...
    time.sleep(0.1)  # be kind; it's a free CDN
```

## `data.json` schema

```jsonc
{
  "title": "Chrono Trigger",                    // canonical display title (string)
  "aliases": ["Chrono Trigger (Japan)"],        // variant titles from other sources
  "year": 1995,                                  // earliest release year, int | null
  "release_dates": {                             // raw date strings per region
    "japan": "August 1995",                      //   keys: japan, north_america, pal,
    "north_america": "August 11, 1995",          //   usa, europe, first_release, other, …
    "first_release": "1995-08-22"                //   keys vary by what sources provided
  },
  "developer": ["Square", "SquareSoft"],         // union across sources (may contain
  "publisher": ["Square"],                       //  naming variants), string[]
  "genre": ["Role-Playing", "Console-style RPG"],// string[]
  "tags": ["fantasy", "rpg", "topdown"],         // community gameplay tags, string[]
  "description": "Take control of…",             // string | null
  "description_source": "snes_csv",              // "snes_csv" | "opengamedb" | "openvgdb"
  "players": "1",                                // string | null, free-form ("1 - 2")
  "languages": ["English, Japanese"],            // string[]
  "roms": [                                      // ROM checksums (OpenVGDB/No-Intro),
    {                                            // headerless; uppercase hex
      "crc32": "05FBB855",                       //   8-char — key used in /by-crc.json
      "md5": "3369347F7663B133CE445C15200A5AFA", //   32-char
      "sha1": "005CCD83…",                       //   40-char
      "region": "Japan",                         //   string, may be ""
      "file": "'96 Zenkoku Koukou Soccer Senshuken (Japan).sfc"  // No-Intro filename
    }
  ],
  "gf_score": 4.58,                              // GameFAQs rating 1–5, float | null
  "metascore": 92,                               // Metacritic 0–100, int | null
  "cover_urls": ["https://…"],                   // external cover image URLs (reference)
  "sources": ["snes_csv", "wikipedia", "openvgdb", "opengamedb"], // provenance
  "images": { "thumb": "thumb.png", "box": "box.jpeg" }  // absent if no local art
}
```

Notes:

- **`year`** is the minimum across all parsed dates — usually the first release
  (Japan), not necessarily your region. Prefer `release_dates` for regional work.
- **`developer` / `publisher`** are union lists; the first entry is from the
  highest-priority source (Wikipedia scrape → Kaggle → OpenVGDB → opengamedb).
- **`images`** is present only when local box art exists; both keys optional
  independently, though in practice they appear together (1,645 games, ~54%).
- **`roms`** holds one entry per known ROM dump of the game (revisions/regions).
  Hashes follow the **No-Intro, headerless** convention in **uppercase hex** —
  this is what emulation DATs and frontends (e.g. Superflix `rom_crc32`)
  standardize on. If your ROM has a copier header (512-byte), strip it before
  hashing or the lookup will miss. `by-crc.json` is the flat CRC32 → slug map
  for O(1) identity resolution; on the ~1-in-10⁷ collision the first slug wins.
- **`cover_urls`** are outbound links (LaunchBox/GameFAQs CDNs) kept for
  reference — GameFAQs' image CDN blocks some datacenter IP ranges.
- Everything not listed (`release_dates` keys beyond the common ones) is raw
  source data passed through; treat unknown keys leniently.

## `catalog.json` schema

Array, sorted by title:

```json
[{
  "slug": "96-zenkoku-koukou-soccer-senshuken",
  "title": "'96 Zenkoku Koukou Soccer Senshuken",
  "year": 1996,
  "developer": "Magical Company",
  "publisher": "Magical Company",
  "genre": "Sports, Traditional, Soccer, Sim",
  "thumb": true
}]
```

`developer`/`publisher` are first-value strings here (not lists), `genre` is a
joined string, `thumb` tells you whether `/<slug>/thumb.png` exists.

## Coverage & provenance

| Field | Filled | Source priority |
|---|---|---|
| year | 89% | Wikipedia (per-region) → Kaggle → OpenVGDB → opengamedb |
| release_dates | 84% | thedevastator/Wikipedia (JP/NA/PAL), OpenVGDB (per region), opengamedb |
| developer | 87% | Wikipedia → Kaggle → OpenVGDB |
| publisher | 78% | Wikipedia → Kaggle (OpenVGDB has none for SNES) |
| description | 70% | Kaggle (GameFAQs-style) → opengamedb (Wikipedia) → OpenVGDB |
| genre / tags | 60% / — | OpenVGDB + opengamedb / Kaggle tags |
| box art (local) | 54% | Kaggle CC0 image set, joined by normalized title |
| gf_score / metascore | 16% / 1% | opengamedb (GameFAQs / Metacritic) |

1,798 of 3,070 records are corroborated by **2+ independent sources** (the rest
are mostly Japan-only releases found by a single source). Records are merged by
normalized exact title, then fuzzy-linked (rapidfuzz ≥ 93) with a
numeric-signature guard that keeps sequels apart (`Hokuto no Ken 5` ≠ `6`).
The full fuzzy-merge audit trail lives in the repo: `data/merge_report.json`.

## Sources & license

Metadata compiled from: Kaggle datasets by sergenkaraoglan (CC0) and
thedevastator, [OpenVGDB v29](https://github.com/OpenVGDB/OpenVGDB),
[karlforshaw/opengamedb](https://github.com/karlforshaw/opengamedb), and
Wikipedia-derived tables. CC0 covers the dataset packaging; **box art remains
copyrighted by its respective publishers** — provided for research/reference.
Pipeline and source scripts: [github.com/mode777/snes-dataset](https://github.com/mode777/snes-dataset).
