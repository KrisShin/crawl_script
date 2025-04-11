import json
import httpx
from loguru import logger

from app.base_spider import BaseSpider
from common.global_variant import ua


class XueqiuIndexSpider(BaseSpider):
    def __init__(self, client: httpx.Client):
        super().__init__(client=client, model=XueqiuIndexSpider)
        self.base_url = (
            'https://stock.xueqiu.com/v5/stock/screener/quote/list.json?page=%d&size=%d&order=desc&order_by=percent&market=%s&type=%s'
        )

    def crawl(self, page: int = 1, size: int = 90, index_type: str = 'sh_sz', market: str = 'CN'):
        logger.info(f'开始获取指数数据: page:{page}, size:{size}, type:{index_type}, market:{market}')
        total = 1
        times = 0
        crawled = 0
        index_list = []
        while crawled < total:
            index_url = self.base_url % (page, size, market, index_type)
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
            self.save(data['list'], {'index_type': index_type})
            # with open(f'index_{index_type}_p{page}.json', 'w') as f:
            #     f.write(str(data['data']['list']))
            page += 1
            times += 1
        with open(f'index_{index_type}.json', 'w') as f:
            f.write(json.dumps(index_list))
        logger.success(f'获取指数数据完成')


if __name__ == '__main__':
    from common.global_variant import proxies

    with httpx.Client(proxies=proxies) as client:
        spider = XueqiuIndexSpider(client)
        spider.crawl()
