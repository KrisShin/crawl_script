import asyncio
import httpx
from loguru import logger

from app.xueqiu.analyze import get_good_zh
from app.xueqiu.spiders.cookie_spider import main as cookie_spider
from app.xueqiu.spiders.index_spider import XueqiuIndexSpider
from app.xueqiu.spiders.user_spider import XueqiuUserSpider
from app.xueqiu.spiders.zh_hostry_spider import XueqiuZHHistorySpider
from app.xueqiu.spiders.zh_index_spider import XueqiuZHSpider
from app.xueqiu.spiders.zh_rebalancing_spider import XueqiuZHRebalancingSpider
from common.global_variant import proxies

TYPE_MARKET_MAPPING = {
    'sh_sz': 'CN',
    'hk': 'HK',
    'us': 'US',
    'convert': 'CN',
    'national': 'CN',
    'corp': 'CN',
    'repurchase': 'CN',
}


def crawl_index():
    for index_type, market in TYPE_MARKET_MAPPING.items():
        with httpx.Client(proxy=proxies) as client:
            page = 1
            if cookie_spider(client):
                spider = XueqiuIndexSpider(client)
                spider.crawl(page=page, index_type=index_type, market=market)


def crawl_zh():
    zh_id = 100389
    max_id = 25800000
    step = 10  # 每个线程爬取的 ID 范围
    while zh_id < max_id:
        with httpx.Client(proxy=proxies) as client:
            if cookie_spider(client):
                spider = XueqiuZHSpider(client)
                spider.crawl(zh_id=zh_id, max_id=zh_id + 10)
                zh_id += step


async def crawl_zh_task(zh_id: int, max_id: int, semaphore: asyncio.Semaphore):
    """单个任务的异步爬取逻辑"""
    async with semaphore:
        try:
            async with httpx.AsyncClient(proxy=proxies) as client:
                # 循环重试 cookie_spider，直到成功
                while True:
                    try:
                        if await cookie_spider(client):
                            break  # 成功获取 cookie，退出循环
                        else:
                            print(f"cookie_spider 失败，等待 20 秒后重试 zh_id={zh_id}")
                            await asyncio.sleep(20)
                            client = await httpx.AsyncClient(proxy=proxies)
                    except Exception as e:
                        print(f"cookie_spider 异常，等待 20 秒后重试 zh_id={zh_id}: {e}")
                        await asyncio.sleep(20)
                        client = await httpx.AsyncClient(proxy=proxies)
                # 执行爬取任务
                spider = XueqiuZHSpider(client)
                await spider.crawl(zh_id=zh_id, max_id=max_id)
            try:
                await client.close()
            except:
                ...
        except Exception as e:
            print(f"任务失败 zh_id={zh_id}: {e}")


async def crawl_zh_async(zh_id: int = 100389, max_id: int = 25800000, coroutine: int = 30):
    # zh_id = 100389
    # max_id = 127000  # 限制最大 ID
    # max_id = 25800000  # 真实最大 ID
    step = 10  # 每个协程爬取的 ID 范围

    semaphore = asyncio.Semaphore(coroutine)  # 创建信号量
    tasks = []

    while zh_id < max_id:
        tasks.append(crawl_zh_task(zh_id, min(zh_id + step, max_id), semaphore))
        zh_id += step

    # 并发运行所有任务，受信号量限制
    await asyncio.gather(*tasks)

    # 爬虫完成时记录日志
    print(f"爬虫任务完成，已爬取到 max_id={max_id}")


async def crawl_zh_history_task(zh_id: int, max_id: int, semaphore: asyncio.Semaphore):
    """单个任务的异步爬取逻辑"""
    async with semaphore:
        try:
            async with httpx.AsyncClient(proxy=proxies) as client:
                # 循环重试 cookie_spider，直到成功
                while True:
                    try:
                        if await cookie_spider(client):
                            break  # 成功获取 cookie，退出循环
                        else:
                            print(f"cookie_spider 失败，等待 20 秒后重试 index={zh_id}")
                            await asyncio.sleep(20)
                            client = await httpx.AsyncClient(proxy=proxies)
                    except Exception as e:
                        print(f"cookie_spider 异常，等待 20 秒后重试 index={zh_id}: {e}")
                        await asyncio.sleep(20)
                        client = await httpx.AsyncClient(proxy=proxies)

                # 执行爬取任务
                spider = XueqiuZHHistorySpider(client)
                await spider.crawl(s_id=zh_id, max_id=max_id)
            try:
                await client.close()
            except:
                ...
        except Exception as e:
            print(f"任务失败 zh_id={zh_id}: {e}")


async def crawl_zh_history_async(zh_id: int = 105040, max_id: int = 1094677, coroutine: int = 5):
    # zh_id = 105040
    # max_id = 150000  # 限制最大 ID
    # max_id = 25800000  # 真实最大 ID
    if not max_id or max_id < zh_id:
        logger.error("max_id 必须大于 u_id")
        return
    step = 10  # 每个协程爬取的 ID 范围

    semaphore = asyncio.Semaphore(coroutine)  # 创建信号量
    tasks = []

    while zh_id < max_id:
        tasks.append(crawl_zh_history_task(zh_id, min(zh_id + step, max_id), semaphore))
        zh_id += step

    # 并发运行所有任务，受信号量限制
    await asyncio.gather(*tasks)

    # 爬虫完成时记录日志
    print(f"爬虫任务完成，已爬取到 max_id={max_id}")


async def crawl_user_task(u_id: int, max_id: int, semaphore: asyncio.Semaphore):
    """爬取用户数据的异步任务"""
    async with semaphore:
        try:
            async with httpx.AsyncClient(proxy=proxies) as client:
                # 循环重试 cookie_spider，直到成功
                while True:
                    try:
                        if await cookie_spider(client):
                            break  # 成功获取 cookie，退出循环
                        else:
                            print(f"cookie_spider 失败，等待 20 秒后重试 zh_id={u_id}")
                            await asyncio.sleep(20)
                            client = await httpx.AsyncClient(proxy=proxies)
                    except Exception as e:
                        print(f"cookie_spider 异常，等待 20 秒后重试 zh_id={u_id}: {e}")
                        await asyncio.sleep(20)
                        client = await httpx.AsyncClient(proxy=proxies)

                # 执行爬取任务
                spider = XueqiuUserSpider(client)
                await spider.crawl(user_index=u_id, max_index=max_id)
            try:
                await client.close()
            except:
                ...
        except Exception as e:
            print(f"任务失败 zh_id={u_id}: {e}")


async def crawl_user_async(u_id: int = 0, max_id: int = 500450, coroutine: int = 5):
    # zh_id = 105040
    # max_id = 150000  # 限制最大 ID
    # max_id = 25800000  # 真实最大 ID
    if not max_id or max_id < u_id:
        logger.error("max_id 必须大于 u_id")
        return
    step = 10  # 每个协程爬取的 ID 范围

    semaphore = asyncio.Semaphore(coroutine)  # 创建信号量
    tasks = []

    while u_id < max_id:
        tasks.append(crawl_user_task(u_id, u_id + step, semaphore))
        u_id += step

    # 并发运行所有任务，受信号量限制
    await asyncio.gather(*tasks)

    # 爬虫完成时记录日志
    print(f"爬虫任务完成，已爬取到 max_id={max_id}")


async def crawl_rebalancing(zh_index: int = 0, max_index: int = 1265067, coroutine: int = 5):
    # zh_id = 105040
    # max_id = 150000  # 限制最大 ID
    # max_id = 25800000  # 真实最大 ID
    if not max_index or max_index < zh_index:
        logger.error("max_id 必须大于 u_id")
        return
    step = 10  # 每个协程爬取的 ID 范围

    with httpx.Client() as client:
        while zh_index < max_index:
            spider = XueqiuZHRebalancingSpider(client, coroutine)
            spider.crawl(zh_index=zh_index, max_index=zh_index + step)
            zh_index += step

    # 爬虫完成时记录日志
    print(f"爬虫任务完成，已爬取到 max_index={max_index}")


async def crawl_user_watch_zh(zh_index: int = 0, max_index: int = 639748, coroutine: int = 5):
    # zh_id = 105040
    # max_id = 150000  # 限制最大 ID
    # max_id = 25800000  # 真实最大 ID
    if not max_index or max_index < zh_index:
        logger.error("max_id 必须大于 u_id")
        return
    step = 10  # 每个协程爬取的 ID 范围

    with httpx.Client() as client:
        while zh_index < max_index:
            spider = XueqiuZHRebalancingSpider(client)
            spider.crawl(zh_index=zh_index, max_index=zh_index + step)
            zh_index += step

    # 爬虫完成时记录日志
    print(f"爬虫任务完成，已爬取到 max_index={max_index}")


async def crawl_user_investment_zh(zh_index: int = 0, max_index: int = 639748, coroutine: int = 5):
    # zh_id = 105040
    # max_id = 150000  # 限制最大 ID
    # max_id = 25800000  # 真实最大 ID
    if not max_index or max_index < zh_index:
        logger.error("max_id 必须大于 u_id")
        return
    step = 10  # 每个协程爬取的 ID 范围

    with httpx.Client() as client:
        while zh_index < max_index:
            spider = XueqiuZHRebalancingSpider(client)
            spider.crawl(zh_index=zh_index, max_index=zh_index + step)
            zh_index += step

    # 爬虫完成时记录日志
    print(f"爬虫任务完成，已爬取到 max_index={max_index}")


async def analyze():
    await get_good_zh()
