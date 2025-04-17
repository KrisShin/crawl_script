import asyncio
import click
from loguru import logger
from common.global_variant import init_db
from app.xueqiu.main import crawl_index, crawl_zh, crawl_zh_async, crawl_zh_history_async, crawl_user_async


def connect_db(db_type: str):
    match db_type:
        case 'mysql':
            asyncio.run(init_db(create_db=False))
            logger.success("Connect Mysql Success")


@click.command()
@click.argument('spider_name', type=click.Choice(['index', 'zh_single', 'zh', 'zh_his', 'user'], case_sensitive=False))
@click.argument('start_id', type=int)
@click.argument('end_id', type=int)
@click.argument('coroutine_count', type=int)
def run_spider(spider_name, start_id: int, end_id: int, coroutine_count: int):
    """
    启动爬虫脚本。

    参数：
    SPIDER_NAME: 爬虫名称，可选值为 'index', 'zh', 'zh_async', 'zh_history_async'
    START_ID: 起始 ID
    END_ID: 结束 ID
    """
    connect_db('mysql')  # 连接数据库

    if spider_name == 'index':
        crawl_index()
    elif spider_name == 'zh_single':
        crawl_zh()  # 单线程爬取
    elif spider_name == 'zh':
        asyncio.run(crawl_zh_async(start_id, end_id, coroutine_count))
    elif spider_name == 'zh_his':
        asyncio.run(crawl_zh_history_async(start_id, end_id, coroutine_count))
    elif spider_name == 'user':
        asyncio.run(crawl_user_async(start_id, end_id, coroutine_count))
    else:
        logger.error(f"未知的爬虫名称: {spider_name}")


if __name__ == '__main__':
    run_spider()
