from datetime import datetime
import json
import random
import httpx
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

from app.base_spider import BaseSpider
from app.xueqiu.model import XueqiuZHHistory
from common.global_variant import ua, mongo_uri, mongo_config

md5_list = [
    'n4%2Bx0DyDgiGQi%3DDCzYDsI3xxAOqIx0KqPiY%2B6Qx',
    'n4AxBDyiDQeQwhDBkox2AYG8DgmYD9G0E1oD',
    'n4jhGKY5D54GhDIx0vk4%2BxCugDfh6Bnpp71oD',
    'n4%2Bxn7i%3DDtGQG%3DGk7D%2FD0iorW4mu8x7IweQ4x',
    'Yui%3D0KGKDIq%2BxCqGXpQIbPitDCBM%2B%2Bo5x',
    'eqGxBDRCi%3DeUD%2FY0xBKD%3DyPY5uIijjGioD',
    'n40xyDuGG%3DdDuq0vd4%2B2DAxqfxmqEqiIp03edx',
    'n4RhAKYKGKBKD5GQGODlxGEI8Lc2epieZiAoD',
    'eqGxR7D%3DG%3Dq4uDBwe5GkbE5AKitDCYz%2Fj%2FfeD',
]


class XueqiuZHHistorySpider(BaseSpider):
    """雪球组合数据爬虫"""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(client=client, model=XueqiuZHHistory)
        self.base_url = 'https://xueqiu.com/cubes/nav_daily/all.json?cube_symbol=%s&md5__1038=%s'

    async def crawl(self, zh_id: int, max_id: int):
        history_list = []
        while zh_id < max_id:
            index_url = self.base_url % (f'ZH{zh_id}', random.choice(md5_list))
            try:
                resp = await self.client.get(index_url, headers={'User-Agent': ua.random}, timeout=30)
                if resp.status_code != 200:
                    if '该组合不存在' in resp.text:
                        zh_id += 1
                        continue
                    logger.error(f'获取组合历史数据失败: {resp.status_code}, {resp.text}')
                    continue
                data = resp.json()
                resp_data = data[0]
                resp_data['history'] = json.dumps(resp_data.pop('list'))
                logger.success(f'获取组合历史数据成功: ZHID:{zh_id}, crawled:1')
                # await self.replace([resp_data])
                # await self.collection.update_one(
                #     {"symbol": resp_data["symbol"]},  # 查询条件，确保 symbol 唯一
                #     {"$set": {**resp_data, "update_time": datetime.now()}},  # 更新内容
                #     upsert=True,  # 如果不存在则插入
                # )
                history_list.append(resp_data)
                # with open(f'xueqiu_zh_id', 'a') as f:
                #     f.write(f'ZH{zh_id}\n')
                zh_id += 1
            except Exception as e:
                logger.error(f'请求失败: {e}')
                continue
        # await self.save(history_list)
        # logger.success(f'获取组合历史数据完成')
        if history_list:
            try:
                mongo_client = AsyncIOMotorClient(mongo_uri)
                db = mongo_client[mongo_config.db_name]
                collection = db["zh_history"]
                update_time = datetime.now()
                # 构建批量操作列表
                operations = [
                    UpdateOne(
                        {"symbol": item["symbol"]},  # 查询条件，确保 symbol 唯一
                        {"$set": {**item, "update_time": update_time}},  # 更新内容
                        upsert=True,  # 如果不存在则插入
                    )
                    for item in history_list
                ]
                # 批量执行操作
                if operations:
                    result = await collection.bulk_write(operations, ordered=False)
                    logger.success(f"成功保存 {result.upserted_count}, 更新{ result.modified_count} 条数据到 MongoDB max_id: {max_id}")
                mongo_client.close()
            except Exception as e:
                from traceback import print_exc

                print_exc()
                logger.error(f"保存到 MongoDB 失败: {e} max_id: {max_id}")


if __name__ == '__main__':
    from common.global_variant import proxies

    async def run():
        async with httpx.AsyncClient(proxies=proxies) as client:
            spider = XueqiuZHHistorySpider(client)
            await spider.crawl(zh_id=100389)

    import asyncio

    asyncio.run(run())
