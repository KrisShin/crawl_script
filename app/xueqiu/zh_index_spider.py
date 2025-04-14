import json
import random
import httpx
from loguru import logger

from app.base_spider import BaseSpider
from app.xueqiu.model import XueqiuZHIndex
from common.global_variant import ua

md5_list = [
    'n4%2Bx0DyDgiGQi%3DDCzYDsI3xxAOqIx0KqPiY%2B6Qx',
    'n4AxBDyiDQeQwhDBkox2AYG8DgmYD9G0E1oD',
    'n4jhGKY5D54GhDIx0vk4%2BxCugDfh6Bnpp71oD',
    'n4%2Bxn7i%3DDtGQG%3DGk7D%2FD0iorW4mu8x7IweQ4x',
    'Yui%3D0KGKDIq%2BxCqGXpQIbPitDCBM%2B%2Bo5x',
    'eqGxBDRCi%3DeUD%2FY0xBKD%3DyPY5uIijjGioD',
    'n40xyDuGG%3DdDuq0vd4%2B2DAxqfxmqEqiIp03edx',
    'n4RhAKYKGKBKD5GQGODlxGEI8Lc2epieZiAoD',
]


class XueqiuZHSpider(BaseSpider):
    """雪球组合数据爬虫"""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(client=client, model=XueqiuZHIndex)
        self.base_url = 'https://xueqiu.com/query/v1/search/cube/stock.json?q=%s&page=1&count=20&md5__1038=%s'

    async def crawl(self, zh_id: int, max_id: int):
        while zh_id < max_id:
            index_url = self.base_url % (f'ZH{zh_id}', random.choice(md5_list))
            try:
                resp = await self.client.get(index_url, headers={'User-Agent': ua.random}, timeout=30)
                if resp.status_code != 200:
                    logger.error(f'获取组合数据失败: {resp.status_code}, {resp.text}')
                    continue
                data = resp.json()
                if data['success'] is False:
                    continue
                try:
                    if data.get('data') not in (None, {}):
                        data = data['data']
                except Exception as e:
                    logger.error(f'获取组合数据失败: {e}, {resp.status_code}, {resp.text}')
                    break
                resp_data = data.get('list', []) + data.get('recommend', [])
                logger.success(f'获取组合数据成功: ZHID:{zh_id}, crawled:{data['recommend_count']}')
                await self.replace(resp_data)
                # with open(f'xueqiu_zh_id', 'a') as f:
                #     f.write(f'ZH{zh_id}\n')
                zh_id += 1
            except Exception as e:
                logger.error(f'请求失败: {e}')
                break
        logger.success(f'获取指数数据完成')


if __name__ == '__main__':
    from common.global_variant import proxies

    async def run():
        async with httpx.AsyncClient(proxies=proxies) as client:
            spider = XueqiuZHSpider(client)
            await spider.crawl(zh_id=100389)

    import asyncio

    asyncio.run(run())
