import httpx
from loguru import logger

from common.global_variant import ua

INDEX_URL = 'https://stock.xueqiu.com/v5/stock/screener/quote/list.json?page=%d&size=%d&order=desc&order_by=percent&market=CN&type=%s'


def main(client: httpx.Client, page: int = 1, size: int = 90, index_type: str = 'sh_sz'):
    total = 1
    crawled = 0
    index_list = []
    while crawled < total:
        index_url = INDEX_URL % (page, size, index_type)
        resp = client.get(index_url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0'}, timeout=30)
        if resp.status_code != 200:
            logger.error(f'获取指数数据失败: {resp.status_code}, {resp.text}')
            continue
        data = resp.json()
        total = data['data']['count']
        crawled += len(data['data']['list'])
        index_list.extend(data['data']['list'])
        page += 1
        with open(f'index_{index_type}_p{page}.json', 'w') as f:
            f.write(str(data['data']['list']))
        logger.success(f'获取指数数据成功: page:{page}, size:{size}, type:{index_type}, crawled:{page*size} total:{total}')
    with open(f'index_{index_type}.json', 'w') as f:
        f.write(str(index_list))
    logger.success(f'获取指数数据完成')


if __name__ == '__main__':
    from common.global_variant import proxies

    with httpx.Client(proxies=proxies) as client:
        main(client)
