from loguru import logger
from tortoise import run_async


class BaseSpider(object):
    """
    基础爬虫类，提供基本的爬虫功能
    """

    def __init__(self):
        self.client = None
        self.model = None

    def save(self, data: list, extra_props: dict):
        bulk_data = []
        for corp in data:
            bulk_data.append(self.model(**corp, **extra_props))
        run_async(self.model.bulk_create(bulk_data))
        logger.success(f'保存数据成功: {len(data)} 条')

    def replace(self, data: list, extra_props: dict):
        for corp in data:
            run_async(self.model.update_or_create(symbol=corp['symbol'], **extra_props, defaults={**corp, **extra_props}))
        logger.success(f'更新数据成功: {len(data)} 条')
