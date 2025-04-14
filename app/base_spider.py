import httpx
from loguru import logger
from tortoise.transactions import in_transaction
from tortoise import models


class BaseSpider(object):
    """
    基础爬虫类, 提供基本的数据存储更新功能
    """

    def __init__(self, client: httpx.Client, model: models.Model):
        self.client = client
        self.model = model

    async def save(self, data: list, extra_props: dict = {}):
        bulk_data = []
        for corp in data:
            bulk_data.append(self.model(**corp, **extra_props))
        await self.model.bulk_create(bulk_data)
        logger.success(f'保存数据成功: {len(data)} 条')

    async def replace(self, data: list, extra_props: dict = {}):
        async with in_transaction():
            for corp in data:
                await self.model.update_or_create(
                    symbol=corp['symbol'],
                    defaults={**corp, **extra_props},
                )
        logger.success(f'更新数据成功: {len(data)} 条')
