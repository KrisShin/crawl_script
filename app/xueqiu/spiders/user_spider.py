from datetime import datetime
import json
import random
import httpx
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

from app.base_spider import BaseSpider
from app.xueqiu.model import XueqiuUser
from common.global_variant import ua, mongo_uri, mongo_config, user_id_list

md5_list = [
    'n40xgD2Dyii%3DYiKPGNDQuPGIQ7KG%3DYesizK74D',
    'n40x0D2iG%3Di%3D0QK4GNuexUxiwInDglGhGlDYupD',
    'n4mx9D0DuDyjj40534%2BhxAxq0xWqY5qKwNI%3Ddx',
    'n4mx9D0DuDyjj40534%2BhxAxq0xWqY5wimedx',
    'n4mx9D0DuDyjj40534%2BhxAxq0xWqY5I34eQ4dx',
    'n4mx9D0DuDyjj40534%2BhxAxq0xWqY5IfX6ftdx',
    'n40x0D2iG=i=0QK4GNuexUxiwInDgGZl2E1oD',
    'n4mx9D0DuDyjj40534%2BhxAxq0xWqY5ANjtQdx',
    'n40x0D2iG=i=0QK4GNuexUxiwInDgG6iiGjCoD',
    'n4mx9D0DuDyjj40534%2BhxAxq0xWqY5Kw66qdx',
    'n40x0D2iG%3Di%3D0QK4GNuexUxiwInDgillGnDYupD',
    'n4mx9D0DuDyjj40534%2BhxAxq0xWqYv%3DPp3qE3x',
]


class XueqiuUserSpider(BaseSpider):
    """雪球组合数据爬虫"""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(client=client, model=XueqiuUser)
        self.base_url = 'https://xueqiu.com/user/show.json?id=%d&md5__1038=%s'

    async def crawl(self, user_index: int, max_index: int):
        user_list = []
        crawl_time = datetime.now()
        while user_index < max_index:
            user_id = user_id_list[user_index]
            index_url = self.base_url % (user_id, random.choice(md5_list))
            try:
                resp = await self.client.get(index_url, headers={'User-Agent': ua.random}, timeout=30)
                if resp.status_code != 200:
                    logger.error(f'获取用户数据失败: {resp.status_code}, {resp.text}')
                    if '用户不存在' in resp.text:
                        user_index += 1
                    continue
                user_data = resp.json()
                logger.success(f'获取用户数据成功: index:{user_index} ID:{user_id}')
                user_list.append(
                    {
                        **user_data,
                        "crawl_time": crawl_time,
                        'verified_infos': user_data['verified_infos'] and json.dumps(user_data['verified_infos']),
                        'national_network_verify': user_data['national_network_verify'] and json.dumps(user_data['national_network_verify']),
                    }
                )
                # with open(f'xueqiu_zh_id', 'a') as f:
                #     f.write(f'ZH{zh_id}\n')
                user_index += 1
            except Exception as e:
                logger.error(f'请求失败: {e}')
                continue
        # await self.save(history_list)
        # logger.success(f'获取组合历史数据完成')
        if user_list:
            try:
                mongo_client = AsyncIOMotorClient(mongo_uri)
                db = mongo_client[mongo_config.db_name]
                collection = db["user"]
                operations = [UpdateOne({"id": item["id"]}, {"$set": item}, upsert=True) for item in user_list]
                # 批量执行操作
                if operations:
                    result = await collection.bulk_write(operations, ordered=False)
                    logger.success(f"成功保存 {result.upserted_count}, 更新{ result.modified_count} 条数据到 MongoDB max_id: {max_index}")
                mongo_client.close()
            except Exception as e:
                from traceback import print_exc

                print_exc()
                logger.error(f"保存到 MongoDB 失败: {e} max_id: {max_index}")


if __name__ == '__main__':
    from common.global_variant import proxies

    async def run():
        async with httpx.AsyncClient(proxies=proxies) as client:
            spider = XueqiuUserSpider(client)
            await spider.crawl(zh_id=0)

    import asyncio

    asyncio.run(run())
