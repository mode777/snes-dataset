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

## Layout

- `scrapy.cfg` — Scrapy project config
- `snes_dataset/` — the Scrapy project (settings, items, pipelines)
- `snes_dataset/spiders/` — one module per target site
- `data/` — crawled output (gitignored)
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

`gamefaqs_list` validated against the archived copy of page 1 (100/100 games
parsed). Full 26-page live crawl pending a non-datacenter IP.
