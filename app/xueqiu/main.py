import httpx
from app.xueqiu.cookie_spider import main as cookie_spider
from app.xueqiu.index_spider import XueqiuIndexSpider, main as index_spider
from common.global_variant import proxies

TYPE_MARKET_MAPPING = {
    'sh_sz': 'CN',
    'hk': 'HK',
    'us': 'US',
    'convert': 'CN',
    'national': 'CN',
    'corp': 'CN',
    'repurchase': 'CN',
}


def main():
    for index_type, market in TYPE_MARKET_MAPPING.items():
        with httpx.Client(proxy=proxies) as client:
            page = 1
            if cookie_spider(client):
                spider = XueqiuIndexSpider(client)
                spider.crawl(page=page, index_type=index_type, market=market)
