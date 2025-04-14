import asyncio
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.xueqiu.cookie_spider import main as cookie_spider
from app.xueqiu.index_spider import XueqiuIndexSpider
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
    async with semaphore:
        try:
            async with httpx.AsyncClient(proxy=proxies) as client:
                if await cookie_spider(client):
                    spider = XueqiuZHSpider(client)
                    await spider.crawl(zh_id=zh_id, max_id=max_id)
        except Exception as e:
            print(f"任务失败 zh_id={zh_id}: {e}")

async def crawl_zh_async():
    zh_id = 100389
    max_id = 110000  # 限制最大 ID
    # max_id = 25800000  # 真实最大 ID
    step = 5  # 每个协程爬取的 ID 范围
    max_concurrent_tasks = 8  # 限制同时运行的协程数量

    semaphore = asyncio.Semaphore(max_concurrent_tasks)  # 创建信号量
    tasks = []

    while zh_id < max_id:
        tasks.append(crawl_zh_task(zh_id, zh_id + step, semaphore))
        zh_id += step

    # 并发运行所有任务，受信号量限制
    await asyncio.gather(*tasks)