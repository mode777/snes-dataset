"""
Generic starting-point spider.

Copy this file, rename the class and `name`, set `start_urls`, and fill in
`parse()` with selectors for the target site. Run with:

    uv run scrapy crawl example -O data/example.jsonl

The HTTP cache is enabled in settings.py, so you can iterate on selectors
without re-downloading pages.
"""

from __future__ import annotations

from typing import ClassVar

import scrapy


class ExampleSpider(scrapy.Spider):
    name = "example"
    # TODO: replace with the real target site
    start_urls: ClassVar[list[str]] = ["https://example.com/"]

    def parse(self, response):
        # TODO: replace with real selectors, e.g.:
        # for row in response.css("table.gamelist tr"):
        #     yield {
        #         "title": row.css("td.title::text").get(),
        #         "url": response.urljoin(row.css("a::attr(href)").get("")),
        #     }
        yield {
            "url": response.url,
            "title": response.css("title::text").get(),
        }
