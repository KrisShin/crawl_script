from datetime import datetime
import json
import time
import random
import httpx
from loguru import logger
from pymongo import UpdateOne, MongoClient

from app.base_spider import BaseSpider
from app.anjuke.model import AnjukeSHCommunity
from common.global_variant import ua, mongo_uri, mongo_config, symbol_all_list, user_cookies


class AnjukeSHCommunitySpider(BaseSpider):
    """雪球组合仓位变动数据爬虫"""

    def __init__(self, client: httpx.AsyncClient, index: int):
        super().__init__(client=client, model=AnjukeSHCommunity)
        self.list_url = 'https://shanghai.anjuke.com/community/o4-p%(page)d/'
        self.info_url = 'https://shanghai.anjuke.com/community/view/%(community_id)d'
        
        self.cookie = ''

    def crawl(self):
        community_page_list = []
        total = 51286
        index = 1
        page = 1
        while index <= total:
            update_time = datetime.now()
            
            while page <= max_page:
                if page > 50:
                    break
                index_url = self.base_url % (symbol_all_list[zh_index], page, random.choice(md5_list))
                try:
                    resp = self.client.get(index_url, headers={'User-Agent': ua.random, 'cookie': self.cookie}, timeout=30)
                    if resp.status_code != 200:
                        logger.error(f'获取组合调仓数据失败: index:{zh_index}, zh_id:{symbol_all_list[zh_index]} code: {resp.status_code}, {resp.text}')
                        time.sleep(120)
                    data = resp.json()
                    if page == 1:
                        max_page = data['maxPage']

                    community_page_list.extend(
                        [
                            {**item, "crawl_time": update_time, 'symbol': symbol_all_list[zh_index], 'rebalancing_histories': json.dumps(item['rebalancing_histories'])}
                            for item in data['list']
                        ]
                    )
                    # with open(f'xueqiu_zh_id', 'a') as f:
                    #     f.write(f'ZH{zh_id}\n')
                    logger.success(f'获取组合调仓数据成功: index: {zh_index} ZHID:{symbol_all_list[zh_index]}, crawled:{len(data["list"])}')
                    page += 1
                except Exception as e:
                    logger.error(f'请求失败: {e}')
                    continue
                time.sleep(1 + random.random() * 3)
            zh_index += 1
        # await self.save(history_list)
        # logger.success(f'获取组合历史数据完成')
        if community_page_list:
            try:
                mongo_client = MongoClient(mongo_uri)
                db = mongo_client[mongo_config.db_name]
                collection = db["zh_rebalancing"]
                # 构建批量操作列表
                operations = [
                    UpdateOne(
                        {"id": item["id"]},  # 查询条件，确保 id 唯一
                        {"$set": item},  # 更新内容
                        upsert=True,  # 如果不存在则插入
                    )
                    for item in community_page_list
                ]
                # 批量执行操作
                if operations:
                    result = collection.bulk_write(operations, ordered=False)
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
            spider = XueqiuZHRebalancingSpider(client)
            await spider.crawl(s_id=100389)

    import asyncio

    asyncio.run(run())
