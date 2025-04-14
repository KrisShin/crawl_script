import asyncio
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.xueqiu.cookie_spider import main as cookie_spider
from app.xueqiu.index_spider import XueqiuIndexSpider
from app.xueqiu.zh_hostry_rank_spider import XueqiuZHHistorySpider
from app.xueqiu.zh_index_spider import XueqiuZHSpider
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
                            client = await httpx.AsyncClient(proxies=proxies)
                    except Exception as e:
                        print(f"cookie_spider 异常，等待 20 秒后重试 zh_id={zh_id}: {e}")
                        await asyncio.sleep(20)
                        client = await httpx.AsyncClient(proxies=proxies)
                # 执行爬取任务
                spider = XueqiuZHSpider(client)
                await spider.crawl(zh_id=zh_id, max_id=max_id)
            try:
                await client.close()
            except:
                ...
        except Exception as e:
            print(f"任务失败 zh_id={zh_id}: {e}")


async def crawl_zh_async():
    zh_id = 100389
    max_id = 127000  # 限制最大 ID
    # max_id = 25800000  # 真实最大 ID
    step = 5  # 每个协程爬取的 ID 范围
    max_concurrent_tasks = 30  # 限制同时运行的协程数量

    semaphore = asyncio.Semaphore(max_concurrent_tasks)  # 创建信号量
    tasks = []

    while zh_id < max_id:
        tasks.append(crawl_zh_task(zh_id, zh_id + step, semaphore))
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
                            print(f"cookie_spider 失败，等待 20 秒后重试 zh_id={zh_id}")
                            await asyncio.sleep(20)
                            client = await httpx.AsyncClient(proxies=proxies)
                    except Exception as e:
                        print(f"cookie_spider 异常，等待 20 秒后重试 zh_id={zh_id}: {e}")
                        await asyncio.sleep(20)
                        client = await httpx.AsyncClient(proxies=proxies)

                # 执行爬取任务
                spider = XueqiuZHHistorySpider(client)
                await spider.crawl(zh_id=zh_id, max_id=max_id)
            try:
                await client.close()
            except:
                ...
        except Exception as e:
            print(f"任务失败 zh_id={zh_id}: {e}")


async def crawl_zh_history_async():
    zh_id = 102380
    max_id = 150000  # 限制最大 ID
    # max_id = 25800000  # 真实最大 ID
    step = 5  # 每个协程爬取的 ID 范围
    max_concurrent_tasks = 10  # 限制同时运行的协程数量

    semaphore = asyncio.Semaphore(max_concurrent_tasks)  # 创建信号量
    tasks = []

    while zh_id < max_id:
        tasks.append(crawl_zh_history_task(zh_id, zh_id + step, semaphore))
        zh_id += step

    # 并发运行所有任务，受信号量限制
    await asyncio.gather(*tasks)

    # 爬虫完成时记录日志
    print(f"爬虫任务完成，已爬取到 max_id={max_id}")
