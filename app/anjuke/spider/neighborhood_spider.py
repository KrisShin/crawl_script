from datetime import datetime
import json
import time
import random
import httpx
from loguru import logger
from pymongo import UpdateOne, MongoClient
from scrapy import Selector

from app.base_spider import BaseSpider
from app.anjuke.model import AnjukeSHCommunity
from common.global_variant import ua, mongo_uri, mongo_config, symbol_all_list, user_cookies


class AnjukeSHCommunitySpider(BaseSpider):
    """雪球组合仓位变动数据爬虫"""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(client=client, model=AnjukeSHCommunity)
        self.list_url = 'https://shanghai.anjuke.com/community/o4-p%(page)d/'
        self.cookie = 'aQQ_ajkguid=DA7643F7-5AC8-47B4-8607-F392953ED21A; sessid=41F935A0-3EF3-40F9-BB5F-553C0FEB8127; ajk-appVersion=; ctid=11; fzq_h=129731d60cffc4697b100b66cdb39bb6_1745828340547_2ce23e2062e54248bb5acc565afbfd56_3063166652; id58=CkwAb2gPOfRcvwU+bEHfAg==; xxzlclientid=49655c5c-7674-42a9-8b76-1745828341642; xxzlxxid=pfmxwFnTkABCGVVi6F3gjdBbaI70CRkqxRPzFj14gjOQ5sUwUCzcY6qVNWsyE7Cs2OoC; twe=2; ajk_member_verify=S%2BQtr7M4uR0BrkPhsMwG4JEgYyJpJoCxs6T5e%2FnRDUk%3D; ajk_member_verify2=MjAxMjU2Nzg5fHl2WmhYT2Z8MQ%3D%3D; fzq_js_anjuke_ershoufang_pc=86484147df97972c27ed3f09db84f4ba_1745828643200_25; obtain_by=2; isp=true; 58tj_uuid=19c943e4-07a2-4baf-b09c-f9e56b3bc352; new_uv=1; als=0; ajk_member_id=201256789; xxzlbbid=pfmbM3wxMDM0NnwxLjEwLjB8MTc0NTgzMzc3ODIwMTk5NDE2OXx3NUFuUnRwbFNhMVBzUmFlMnN3ZTFuL2JUelA4OGhrLzhmVzFRVGlqK3RFPXw3NWJjOWE2ZGY4YmI0NzEyMDRmZmQ3YmI3Zjk3Yjg2NF8xNzQ1ODMzNzc2OTAzXzgwODlkMGEzZGE0MTRlMWI5YTNhZDI0YThiMTBkMzZlXzMwNjMxNjY2NTJ8ZWM3ZGUxMTliMDYxNmQ4ZTA2Nzc3MTdmNGU3ZjVkYWRfMTc0NTgzMzc3Njk1MV8yNTQ=; ajkAuthTicket=TT=9d41d8663ba7d7cd387b0e6e1c32d597&TS=1745834197504&PBODY=cdbPBRJqNgFmPqYFj_6IlL73OT89uxjHBPhS3xJsc7ze0OWD90aShcOYEZOHbV8AgMWq9-XSFeTamN_YNxhxmNZtJIw7hYuEkBL9vSr_7I3ImvOt77wWKC6uRqVurkFld1VRQNuGgnMDlxAtzc25-tDKNsGcjNDDaQq0i0kJy_w&VER=2&CUID=IaMzr4tsYoGtAgumkRBfOBFWXp57TMBP; fzq_js_anjuke_xiaoqu_pc=bd102becc2ad7663f80ee8e14bbcd69c_1745834198609_25'

    async def crawl(self):
        community_page_list = []
        total = 51286
        index = 1
        page = 1
        while index <= total:
            url_list = self.parse_list(page)
            for url in url_list:
                community_info = self.parse_info(url)
                index += 1
            if community_page_list:
                await self.save(community_page_list)
            logger.info(f'第 {page} 页数据爬取完成, 共 {len(community_page_list)} 条数据')
            page += 1

    def parse_list(self, page: int) -> list:
        """解析列表页"""
        # 解析列表页数据
        # 这里需要根据实际的 HTML 结构进行解析
        # 返回一个包含所有社区信息的列表
        try:
            index_url = self.list_url % {'page': page}
            resp = self.client.get(index_url, headers={'User-Agent': ua.random, 'cookie': self.cookie}, timeout=30)
            if resp.status_code != 200:
                logger.error(f'获取小区列表失败: page:{page}')
                time.sleep(120)
            selector = Selector(text=resp.text)
            community_list = selector.xpath('//*[@id="__layout"]/div/section/section[3]/section/div[2]/a/@href').getall()
            return community_list
        except Exception as e:
            from traceback import print_exc

            print_exc()
            logger.error(f'请求失败: {e}')

    def parse_info(self, info_url: int) -> dict:
        """解析小区详情页"""
        # 解析详情页数据
        # 这里需要根据实际的 HTML 结构进行解析
        # 返回一个包含小区信息的字典
        try:
            resp = self.client.get(info_url, headers={'User-Agent': ua.random, 'cookie': self.cookie}, timeout=30)
            if resp.status_code != 200:
                logger.error(f'获取小区详情失败: url:{info_url}')
                time.sleep(120)
            selector = Selector(text=resp.text)
            community_info = selector.xpath('//*[@id="__layout"]/div/div[2]/div[3]/div[2]/div[1]/div[2]/div/div').getall()
            return community_info
        except Exception as e:
            from traceback import print_exc

            print_exc()
            logger.error(f'请求失败: {e}')
