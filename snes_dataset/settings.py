# Scrapy settings for snes_dataset project
#
# Docs: https://docs.scrapy.org/en/latest/topics/settings.html

BOT_NAME = "snes_dataset"

SPIDER_MODULES = ["snes_dataset.spiders"]
NEWSPIDER_MODULE = "snes_dataset.spiders"

ADDONS = {}

# Crawl responsibly by identifying yourself (and your website) on the user-agent.
# TODO: point this at a real contact (GitHub profile or email) before crawling.
USER_AGENT = "snes-dataset-crawler/0.1 (https://github.com/mode777/snes-dataset)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Concurrency and throttling — keep this gentle, we are building a dataset,
# not DDoS-ing a fan site.
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 1

# AutoThrottle adapts the delay to server latency within these bounds.
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 15.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# Retry transient failures
RETRY_TIMES = 3

# HTTP cache: lets you re-run spiders against cached pages while developing
# selectors, without hammering the site. Flip to False (or remove) for real runs.
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 60 * 60 * 24 * 7
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Item pipelines
#ITEM_PIPELINES = {
#    "snes_dataset.pipelines.SnesDatasetPipeline": 300,
#}

# Feed exports — `scrapy crawl <spider> -O data/<name>.jsonl`
FEED_EXPORT_ENCODING = "utf-8"

LOG_LEVEL = "INFO"
