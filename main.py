import asyncio
import click
from loguru import logger
from app.research_report.rmi_spider import main as run_rmi_crawl
from app.charging_alliance_news.spider import main as charging_alliance_news
from app.xueqiu.script.import_rebalancing import import_reb
from common.global_variant import init_db
from app.xueqiu.main import (
    analyze,
    contrib,
    crawl_index,
    crawl_rebalancing,
    crawl_zh,
    crawl_zh_async,
    crawl_zh_history_async,
    crawl_user_async,
)
from app.nea_news.spider import main as crawl_nea_news


def connect_db(db_type: str):
    match db_type:
        case "mysql":
            asyncio.run(init_db(create_db=False))
            logger.success("Connect Mysql Success")


@click.command()
@click.argument(
    "spider_name",
    type=click.Choice(
        ["index", "zh_single", "zh", "zh_his", "user", "reb", "ana", "ctb", "rmi", "news", "charging_alliance"],
        case_sensitive=False,
    ),
    required=False,
)
@click.argument("start_id", type=int, required=False)
@click.argument("end_id", type=int, required=False)
@click.argument("coroutine_count", type=int, required=False)
def run_spider(spider_name, start_id: int, end_id: int, coroutine_count: int):
    """
    启动爬虫脚本。

    参数：
    SPIDER_NAME: 爬虫名称，可选值为 'index', 'zh', 'zh_async', 'zh_history_async'
    START_ID: 起始 ID
    END_ID: 结束 ID
    """
    connect_db("mysql")  # 连接数据库

    if spider_name == "rmi":
        # 注意: Scrapy 爬虫不需要 connect_db, 除非你在 pipeline 中自己实现
        asyncio.run(run_rmi_crawl())
    elif spider_name == "index":
        crawl_index()
    elif spider_name == "zh_single":
        crawl_zh()  # 单线程爬取
    elif spider_name == "zh":
        asyncio.run(crawl_zh_async(start_id, end_id, coroutine_count))
    elif spider_name == "zh_his":
        asyncio.run(crawl_zh_history_async(start_id, end_id, coroutine_count))
    elif spider_name == "user":
        asyncio.run(crawl_user_async(start_id, end_id, coroutine_count))
    elif spider_name == "reb":
        asyncio.run(crawl_rebalancing(start_id, end_id, coroutine_count))
    elif spider_name == "ana":
        asyncio.run(analyze())
    elif spider_name == "ctb":
        asyncio.run(contrib(start_id))
    elif spider_name == "news":
        asyncio.run(crawl_nea_news())
    elif spider_name == "charging_alliance":
        asyncio.run(charging_alliance_news())
    else:
        logger.error(f"未知的爬虫名称: {spider_name}")


if __name__ == "__main__":
    run_spider()

    # import json
    # with open('./user_id.json', 'r') as f:
    #     data = json.load(f)
    # with open('./user_id.json', 'w') as f:
    #     f.write(json.dumps([item['owner_id'] for item in data]))
    # print(len(data))
    # from tortoise import run_async

    # run_async(import_reb())
