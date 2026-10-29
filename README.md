# snes-dataset

Scripts and tooling for crawling web sources and building a SNES dataset.

Built with **Python + Scrapy** (static-HTML targets, run from this container).

## Setup

Requires [uv](https://docs.astral.sh/uv/) (preinstalled in the toolbox container).

```sh
uv sync                 # creates .venv from uv.lock (Python 3.13, pinned)
```

> Note: pinned to Python **3.13** deliberately — uv 0.8.x's managed CPython 3.12
> musl build has a broken SOABI tag that breaks binary wheels (lxml etc.) on
> Alpine. See [uv#16349](https://github.com/astral-sh/uv/issues/16349).

## Public static dataset

The merged dataset is published as a browsable static tree on GitHub Pages:

**https://mode777.github.io/snes-dataset/**

- `index.json` — `{ "<kebab-slug>": "<Original Title>" }` for all ~3.0k games
- `<slug>/data.json` — full metadata for one game; images referenced by filename
- `<slug>/thumb.png` / `<slug>/box.jpeg` — box art (small/large Kaggle sets), when available

Rebuild with `uv run python scripts/build_public.py` (requires the merge step first).
Deployed automatically by `.github/workflows/pages.yml` on every push to `main`.

> Attribution: data compiled from Kaggle (sergenkaraoglan, thedevastator — CC0),
> OpenVGDB, opengamedb and Wikipedia-derived sources. Box art remains the
> copyright of its respective publishers; provided here for research/reference.

## GameFAQs list crawler

`snes_dataset/spiders/gamefaqs_list.py` crawls the SNES "all games" overview
(26 paginated pages, ~100 games each) and emits one JSON object per game:

```json
{"title": "'96 Zenkoku Koukou Soccer Senshuken", "url": "https://gamefaqs.gamespot.com/snes/571436-96-zenkoku-koukou-soccer-senshuken"}
```

```sh
# validation mode: parses the Internet Archive copy of page 1 (works anywhere)
uv run scrapy crawl gamefaqs_list -a wayback=latest -O data/gamefaqs_snes_list.json

# full crawl (26 pages) — run from an IP GameFAQs does not block, see below
uv run scrapy crawl gamefaqs_list -O data/gamefaqs_snes_list.json
```

### The Cloudflare / IP-block situation

GameFAQs sits behind Cloudflare **and** blocks hosting-provider IP ranges at
the WAF level. From a datacenter IP you get either the JS challenge (403) or a
plain 400: *"Due to abuse from this hosting service, all interactive traffic
is blocked."* Verified 2026-10 — no fingerprint trickery helps, and an honest
crawler UA does not whitelist you from those ranges. Ways forward:

1. **Run the crawl from a residential IP** (your own machine). The repo is
   self-contained: `uv sync`, then the `scrapy crawl` command above. Politeness
   is already configured (robots.txt obeyed, 1 req/domain, ~1 s + AutoThrottle).
   Check the site's robots.txt/ToS from your browser first.
2. **GameFAQs Contributed Data API** — the sanctioned programmatic route if
   you qualify as a contributor: https://gamefaqs.gamespot.com/api/contributors
3. **Wayback Machine** — `wayback=latest` mode parses the archived copy; only
   page 1 of the list is archived, so it's for selector testing, not the dataset.
4. Not recommended: challenge-solving proxies (FlareSolverr etc.) — this is a
   deliberate block, and circumventing it risks the IP (yours) being banned.

## Build the dataset

Merge all sources into one dataset (no crawling needed):

```sh
uv run python scripts/download_sources.py          # metadata (~15 MB)
uv run python scripts/download_sources.py --images # + 232 MB box art zip
uv run python scripts/merge_sources.py             # -> data/snes_merged.json
```

Output (gitignored): `data/snes_merged.json` — one record per game (~3.0k),
`data/merge_report.json` — row counts, field coverage, fuzzy-merge audit list.

Box art sets (Kaggle/sergenkaraoglan, CC0): **small** = 1,772 PNGs, ~72 MB total
(~41 KB, 140×186 thumbnails) vs **large** = 1,772 JPEGs, ~158 MB, inconsistent
dimensions (mostly ~700×512 landscape scans, some portrait). The small set is
the tidy one; both are joined by normalized title.

## Layout

- `scrapy.cfg` — Scrapy project config
- `snes_dataset/` — the Scrapy project (settings, items, pipelines)
- `snes_dataset/spiders/` — one module per target site
- `scripts/download_sources.py` — fetch all dataset sources into `data/`
- `scripts/merge_sources.py` — merge sources by (fuzzy) title into one dataset
- `docs/data-sources.md` — source comparison + licenses
- `data/` — crawled/merged output (gitignored)
- `.scrapy/` — HTTP cache for re-running parses offline (gitignored)

## Usage

List spiders, then crawl one (output as JSON lines):

```sh
uv run scrapy list
uv run scrapy crawl example -O data/example.jsonl
```

To start a new target, copy `snes_dataset/spiders/example.py`, rename the class
and `name`, set `start_urls`, and fill in `parse()` selectors.

## Crawl etiquette (defaults enforced in settings.py)

- `ROBOTSTXT_OBEY = True`
- 1 concurrent request per domain, ~1s delay, AutoThrottle on
- Identifiable User-Agent — **set a real contact URL before crawling**
- HTTP cache enabled so selector work doesn't re-download pages

## Data sources

See [docs/data-sources.md](docs/data-sources.md) — research on datasets/APIs (recommendation: start from the CC0 Kaggle pair + IGDB, not crawling).

## Status

Dataset pipeline working: 6 sources merged into ~3.0k SNES records
(year 89%, developer 87%, publisher 78%, description 70%, box art 53%).
GameFAQs spider validated but parked (IP block — see above). IGDB enrichment
(screenshots, remaining gaps) planned next — needs a Twitch API key.
