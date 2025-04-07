import scrapy


class CrawlSpider(scrapy.Spider):
    name = "crawl"
    allowed_domains = ["snowball"]
    start_urls = ["https://snowball"]

    def parse(self, response):
        pass
