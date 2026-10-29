# snes-dataset

A static, publishable dataset of **3,070 SNES games** — metadata, per-region
release dates, ROM checksums, and box art — merged from open sources and
served as a simple JSON "API" on GitHub Pages.

**Live:** https://mode777.github.io/snes-dataset/ ·
**API & schema docs:** [docs/API.md](docs/API.md)

## The "API"

| Path | Description |
|---|---|
| `/index.json` | `{ "<Original Title>": "<slug>" }` — title → folder |
| `/index-reverse.json` | `{ "<slug>": "<Original Title>" }` — folder → title |
| `/catalog.json` | one lightweight record per game (powers the grid UI) |
| `/by-crc.json` | `{ "<CRC32>": "<slug>" }` — exact ROM identity (uppercase hex) |
| `/<slug>/data.json` | full metadata incl. `roms[]` checksums |
| `/<slug>/thumb.png`, `/<slug>/box.jpeg` | box art, when available (1,645 games) |
| `/<slug>/snap.png` | in-game screenshot (libretro), when available (2,133 games) |

`index.html` is a dependency-free browser over this API: search, cover grid,
filters, detail views with `#slug` deep links. Full schema, usage examples and
coverage numbers in [docs/API.md](docs/API.md) (also served as `/README.md`).

## Build the dataset

```sh
uv sync                                             # Python 3.13, pinned (.python-version)
uv run python scripts/download_sources.py           # metadata (~15 MB)
uv run python scripts/download_sources.py --images  # + 232 MB box art zip
uv run python scripts/merge_sources.py              # -> data/snes_merged.json
uv run python scripts/build_public.py               # -> public/ (indexes, data.json, images)
uv run python scripts/download_snaps.py             # -> data/snaps/ (libretro screenshots)
uv run python scripts/build_public.py               # again: copies snaps into public/
```

Outputs (all in gitignored `data/`): `snes_merged.json` (one record per game),
`merge_report.json` (row counts, field coverage, fuzzy-merge audit list).
`build_public.py` regenerates `public/` except committed shell files
(`index.html`) and copies `docs/API.md` to `public/README.md`.

Box art sets (Kaggle/sergenkaraoglan, CC0): **small** = 1,772 PNGs, ~72 MB
(~41 KB, 140×186 thumbnails) vs **large** = 1,772 JPEGs, ~158 MB, inconsistent
dimensions. Both are kept and joined by normalized title.

## Layout

- `scripts/download_sources.py` — fetch all dataset sources into `data/`
- `scripts/merge_sources.py` — merge sources by (fuzzy) title into one dataset
- `scripts/build_public.py` — build the `public/` static tree + indexes
- `scripts/download_snaps.py` — fetch libretro screenshots into `data/snaps/`
- `public/index.html` — the committed browser UI shell
- `docs/API.md` — API usage + data schema (served as `/README.md`)
- `docs/data-sources.md` — source comparison + licenses
- `data/` — downloaded & merged data (gitignored); `public/` is committed
- `.github/workflows/pages.yml` — deploys `public/` on every push to `main`

## Data sources

See [docs/data-sources.md](docs/data-sources.md). In short: Kaggle CC0 pair
(metadata + box art), thedevastator Wikipedia scrape (per-region dates),
OpenVGDB v29 (covers, genres), karlforshaw/opengamedb (scores). No crawling
involved — direct GameFAQs access is blocked from hosting IPs, and open
datasets cover everything it offered.

> Attribution: data compiled from the sources above (Kaggle sets are CC0).
> Box art remains the copyright of its respective publishers; provided here
> for research/reference. See [LICENSE](LICENSE).

## License

[CC0 1.0](LICENSE) — the merged metadata and pipeline code are dedicated to
the public domain. This does not and cannot cover the box art images, which
remain the property of their publishers; they are distributed as
research/reference only.

## Status

Pipeline working end-to-end; site auto-deploys on push. IGDB enrichment
(screenshots + remaining field gaps) is the next logical step — needs a
Twitch API key.
