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

## Status

Work in progress — no real spiders yet; `example` is a template.
