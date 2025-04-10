import json
import httpx
from loguru import logger
from tortoise import run_async

from app.xueqiu.model import SnowBallIndex
from common.global_variant import ua

INDEX_URL = 'https://stock.xueqiu.com/v5/stock/screener/quote/list.json?page=%d&size=%d&order=desc&order_by=percent&market=%s&type=%s'


def main(client: httpx.Client, page: int = 1, size: int = 90, index_type: str = 'sh_sz', market: str = 'CN'):
    logger.info(f'开始获取指数数据: page:{page}, size:{size}, type:{index_type}, market:{market}')
    total = 1
    times = 0
    crawled = 0
    index_list = []
    while crawled < total:
        index_url = INDEX_URL % (page, size, market, index_type)
        resp = client.get(index_url, headers={'User-Agent': ua.random}, timeout=30)
        if resp.status_code != 200:
            logger.error(f'获取指数数据失败: {resp.status_code}, {resp.text}')
            continue
        data = resp.json()
        try:
            if data.get('data') not in (None, {}):
                data = data['data']
            if times == 0:
                total = data['count']
        except Exception as e:
            logger.error(f'获取指数数据失败: {e}, {resp.status_code}, {resp.text}')
            break
        crawled += len(data['list'])
        index_list.extend(data['list'])
        logger.success(f'获取指数数据成功: page:{page}, size:{size}, type:{index_type}, crawled:{crawled} total:{total}')
        create_by_orm(data['list'], index_type)
        # with open(f'index_{index_type}_p{page}.json', 'w') as f:
        #     f.write(str(data['data']['list']))
        page += 1
        times += 1
    with open(f'index_{index_type}.json', 'w') as f:
        f.write(json.dumps(index_list))
    logger.success(f'获取指数数据完成')


def create_by_orm(data: list, index_type: str = 'sh_sz'):
    bulk_data = []
    for corp in data:
        bulk_data.append(SnowBallIndex(**corp, index_type=index_type))
    run_async(SnowBallIndex.bulk_create(bulk_data))
    logger.success(f'保存数据成功: {len(data)} 条')


def replace_by_orm(data: list, index_type: str = 'sh_sz'):
    for corp in data:
        run_async(SnowBallIndex.update_or_create(symbol=corp['symbol'], type=index_type, defaults={**corp, 'type': index_type}))
    logger.success(f'更新数据成功: {len(data)} 条')


if __name__ == '__main__':
    from common.global_variant import proxies

    with httpx.Client(proxies=proxies) as client:
        main(client)
