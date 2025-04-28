import httpx

from app.anjuke.spider.neighborhood_spider import AnjukeSHCommunitySpider


async def fetch_anjuke():
    with httpx.Client() as client:
        spider = AnjukeSHCommunitySpider(client)
        await spider.crawl()
