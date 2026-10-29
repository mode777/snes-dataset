"""
GameFAQs SNES "all games" list crawler.

Crawls the paginated category overview (26 pages, ~100 games each) and emits
one item per game: {"title": ..., "url": ...}.

Run (live site — needs to run from an IP GameFAQs does not block, see README):

    uv run scrapy crawl gamefaqs_list -O data/gamefaqs_snes_list.json

Test/validation mode against the Internet Archive copy of page 1 (works from
anywhere, Cloudflare-free, but only page 1 is archived):

    uv run scrapy crawl gamefaqs_list wayback=latest -O data/gamefaqs_snes_list.json
"""

from __future__ import annotations

import re
from typing import ClassVar

import scrapy

# Wayback Machine rewrites links to /web/<timestamp>/<original_url>
_WAYBACK_HREF = re.compile(r"^/web/\d+[a-z_]*/(https?://.+)$")


class GameFaqsListSpider(scrapy.Spider):
    name = "gamefaqs_list"
    allowed_domains: ClassVar[list[str]] = [
        "gamefaqs.gamespot.com",
        "web.archive.org",
    ]

    list_url: ClassVar[str] = "https://gamefaqs.gamespot.com/snes/category/999-all"

    def __init__(self, wayback: str | None = None, *args, **kwargs):
        """`wayback=<timestamp|latest>` crawls the archived copy instead of the live site."""
        super().__init__(*args, **kwargs)
        self.wayback = wayback

    async def start(self):
        url = self.list_url
        if self.wayback:
            # "latest" -> Wayback shorthand "2" = nearest capture to now
            ts = "2" if self.wayback == "latest" else self.wayback
            url = f"https://web.archive.org/web/{ts}/{url}"
        yield scrapy.Request(url, meta={"wayback": bool(self.wayback)})

    def parse(self, response):
        wayback = response.meta.get("wayback", False)

        if not wayback:
            # Schedule every page from the pagination jump-menu (0..25 as of
            # writing). Skip 0: the start request already covers page 1.
            for value in response.css("#pagejump option::attr(value)").getall():
                if value != "0":
                    yield response.follow(f"?page={value}", meta={"wayback": wayback})

        # The overview table: class was "results" in the 2026 snapshots,
        # "result" in older markup — match both.
        for row in response.css("table.results tr, table.result tr"):
            link = row.css("td.rtitle a")
            href = link.attrib.get("href")
            title = link.css("::text").get()
            if not href or not title:
                continue
            if wayback and (match := _WAYBACK_HREF.match(href)):
                href = match.group(1)
            yield {"title": title.strip(), "url": response.urljoin(href)}
