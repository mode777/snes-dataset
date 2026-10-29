class SnesDatasetSpiderMiddleware:
    """Spider middleware stub — extend as needed."""

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        yield from result

    def process_start_items(self, start_items, spider):
        yield from start_items

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s", spider.name)


class SnesDatasetDownloaderMiddleware:
    """Downloader middleware stub — extend as needed."""

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        return None

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        return None

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s", spider.name)
