import httpx
from apps.xueqiu.cookie_spider import main as cookie_spider
from apps.xueqiu.index_spider import main as index_spider
from common.global_variant import proxies

TYPE_LIST = ['us', 'cyb', 'sh_sz', 'hk', 'convert', 'national', 'corp', 'repurchase']


def main():
    with httpx.Client(proxy=proxies) as client:
        if cookie_spider(client):
            index_spider(client, index_type='sh_sz')
