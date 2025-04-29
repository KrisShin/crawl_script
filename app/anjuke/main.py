import httpx

from app.anjuke.spider.neighborhood_spider import AnjukeSHCommunitySpider


async def fetch_anjuke(page: int = 1):
    with httpx.Client() as client:
        spider = AnjukeSHCommunitySpider(client, page)
        await spider.crawl()
