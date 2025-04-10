import httpx
from app.xueqiu.cookie_spider import main as cookie_spider
from app.xueqiu.index_spider import main as index_spider
from common.global_variant import proxies

TYPE_MARKET_MAPPING = {
    # 'sh_sz': 'CN',
    # 'hk': 'HK',
    # 'us': 'US',
    'convert': 'CN',
    'national': 'CN',
    'corp': 'CN',
    'repurchase': 'CN',
}


def main():
    for index_type, market in TYPE_MARKET_MAPPING.items():
        with httpx.Client(proxy=proxies) as client:
            if cookie_spider(client):
                page = 1
                # if index_type == 'us':
                #     page = 39
                index_spider(client, page=page, index_type=index_type, market=market)
