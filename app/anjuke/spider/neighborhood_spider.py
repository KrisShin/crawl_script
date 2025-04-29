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
from common.global_variant import (
    ua,
    mongo_uri,
    mongo_config,
    symbol_all_list,
    user_cookies,
)


class AnjukeSHCommunitySpider(BaseSpider):
    """雪球组合仓位变动数据爬虫"""

    def __init__(self, client: httpx.AsyncClient, page: int):
        super().__init__(client=client, model=AnjukeSHCommunity)
        self.list_url = "https://shanghai.anjuke.com/community/o4-p%(page)d/"
        self.cookie = "SECKEY_ABVK=6XiiQzTYeIvQnOkpKYEDyS2zg95GWLSXAts0iAjpfnE%3D; BMAP_SECKEY=pDS2eSVV-fJbKdVVgwy-fVm4ajEMge1gE-Eevhaulhufc-KE5LiE3gAD5ySxOsnOJpvrk3ITQV6e3COSa3RIfWy0cUOdE5jrMw0lLSTAh61VJoWHE8A8d9fOR4hsCqVS__LNN5bjk22d1fWmU1w7W2SBrMoKIoHPga00L5uwNS1nyp6EZZxBSfB77sTSmmIqyvdhRZDBKsjTBJUqwasgxA; aQQ_ajkguid=F9E10FC3-BCF4-467B-8EFE-D567009570A9; sessid=9E2CBCB6-9705-4B37-9BE6-606C234CBC3A; ajk-appVersion=; ctid=11; fzq_h=990ec7e3c9a331d3619681bea4bfd4b6_1745845496848_60c48df8c93c422d8902663f5dccf0f9_47896391075211898812631276241103304807; id58=CkwAUmgPfPloSil/BlgjAg==; xxzlclientid=f5ead13f-ac53-43c5-974b-1745845501063; xxzlxxid=pfmxKR5c3Kpgz1IQ0ty3hlHhLXX0nek4a4qw8rD4NLSRR80AqY80mzeXIbZnTE4PLPdl; obtain_by=2; twe=2; ajk_member_verify=S%2BQtr7M4uR0BrkPhsMwG4JEgYyJpJoCxs6T5e%2FnRDUk%3D; ajk_member_verify2=MjAxMjU2Nzg5fHl2WmhYT2Z8MQ%3D%3D; ajk_member_id=201256789; fzq_js_anjuke_xiaoqu_pc=2818300e4a92e36db31733cb97645016_1745850070919_24; ajkAuthTicket=TT=56f17e630f4b72005afb02d2e063ad72&TS=1745850069575&PBODY=lk0t6qqazUp7zFBYWg3JOb_Yk-xpYBMI4hzxcv6M1iv01kYJNf5Q65X8Np-mrCI4bHdmN7vcJfALokweS7iTVxxSjjNOm5WE0L5VjTw6Jw6v8tjSMeUnM25Wdou6OZkoO3n65IIS7yeUel4iD8Bj5RshlSCrL82ZEYPJnYCXGKU&VER=2&CUID=IaMzr4tsYoGtAgumkRBfOBFWXp57TMBP; xxzlbbid=pfmbM3wxMDM0NnwxLjEwLjF8MTc0NTg1MDA3MjgyMTAxMzg3MHwvZzZvYlFjQXRYK3ZQclJwTlVMVFZpMXN3enZYWW9VS3AvdXkwYTFCOGtzPXw0MzQ5NGU4YjY3ZTEyNDcxYjRiZjljN2Y5ZjY2MzgwNF8xNzQ1ODUwMDY5NjQzXzEyYzU3MmI5ZTIyYzRiOWM4ZTEyMTQwYjljYTE5Yjc4XzQ3ODk2MzkxMDc1MjExODk4ODEyNjMxMjc2MjQxMTAzMzA0ODA3fGUwZmEyODgxYzI2Yjk0ZTI0NjFlYmI5MGNmZDAzNTkzXzE3NDU4NTAwNzIzMzBfMjU0"
        self.page = page

    async def crawl(self):
        total = 51286
        index = 1
        while index <= total:
            url_list = self.parse_list(self.page)
            time.sleep(30 + random.randint(5, 15))

            for url in url_list:
                while True:
                    try:
                        community_info = self.parse_info(url)
                        community_info.update(
                            {
                                "id": int(url.split("/")[-1]),
                                "name": community_info["name"],
                                "property_type": community_info["物业类型"],
                                "ownership_type": community_info["权属类别"],
                                "completion_year": community_info["竣工时间"] and int(community_info["竣工时间"][:-1]),
                                "property_years": community_info["产权年限"] and int(community_info["产权年限"][:-1]),
                                "total_households": community_info["总户数"] and int(community_info["总户数"][:-1]),
                                "total_building_area": community_info["总建面积"] and float( community_info["总建面积"][:-1] ),
                                "plot_ratio": community_info["容积率"] and float(community_info["容积率"]),
                                "greening_rate": community_info["绿化率"] and float(community_info["绿化率"][:-1]),
                                "building_type": community_info["建筑类型"],
                                "business_circle": community_info["所属商圈"],
                                "unified_heating": community_info["统一供暖"] == "是",
                                "water_electricity_type": community_info["供水供电"],
                                "parking_spaces_info": community_info["停车位"] and int( community_info["停车位"].split("(")[0] ),
                                "property_fee": community_info["物业费"] and float( community_info["物业费"].split("元")[0] ),
                                "parking_fee": community_info["停车费"],
                                "parking_management_fee": community_info["车位管理费"],
                                "property_company": community_info["物业公司"],
                                "address": community_info["小区地址"],
                                "developer": community_info["开发商"],
                            }
                        )
                        await AnjukeSHCommunity.update_or_create(
                            id=community_info["id"], defaults=community_info
                        )
                        time.sleep(30 + random.randint(5, 15))
                        break
                    except Exception as err:
                        from traceback import print_exc

                        print_exc()
                        time.sleep(30 + random.randint(5, 15))
                logger.info(f"第 {index}/{total} 条信息爬取完毕")
                index += 1
            logger.info(f"第 {self.page} 页数据爬取完成")
            self.page += 1
            time.sleep(50 + random.randint(5, 15))

    def parse_list(self, page: int) -> list:
        """解析列表页"""
        # 解析列表页数据
        # 这里需要根据实际的 HTML 结构进行解析
        # 返回一个包含所有社区信息的列表
        try:
            index_url = self.list_url % {"page": page}
            resp = self.client.get(
                index_url,
                headers={"User-Agent": ua.random, "cookie": self.cookie},
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error(f"获取小区列表失败: page:{page}")
                time.sleep(120)
            selector = Selector(text=resp.text)
            community_list = selector.xpath(
                '//*[@id="__layout"]/div/section/section[3]/section/div[2]/a/@href'
            ).getall()
            logger.success(f"获取小区列表成功: page:{page}")
            return community_list
        except Exception as e:
            from traceback import print_exc

            print_exc()
            logger.error(f"请求失败: {e}")

    def parse_info(self, info_url: int) -> dict:
        """解析小区详情页"""
        # 解析详情页数据
        # 这里需要根据实际的 HTML 结构进行解析
        # 返回一个包含小区信息的字典
        try:
            resp = self.client.get(
                info_url,
                headers={"User-Agent": ua.random, "cookie": self.cookie},
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error(f"获取小区详情失败: url:{info_url}")
                time.sleep(120)
            selector = Selector(text=resp.text)
            community_key = selector.xpath(
                '//*[@id="__layout"]/div/div[2]/div[3]/div[2]/div[1]/div[2]/div/div/div[1]/text()'
            ).getall()
            community_values1 = selector.xpath(
                '//*[@id="__layout"]/div/div[2]/div[3]/div[2]/div[1]/div[2]/div/div/div[2]/div[1]/text()'
            ).getall()
            community_values2 = selector.xpath(
                '//*[@id="__layout"]/div/div[2]/div[3]/div[2]/div[1]/div[2]/div/div[position()>14]/div[2]/text()'
            ).getall()
            resp = dict(
                zip(
                    community_key,
                    [
                        None if "暂无" in v else v.strip()
                        for v in community_values1 + community_values2
                    ],
                )
            )
            resp["name"] = selector.xpath(
                "/html/body/div[1]/div/div/div[2]/div[2]/div/h1/text()"
            ).getall()[0]
            return resp
        except Exception as e:
            from traceback import print_exc

            print_exc()
            logger.error(f"请求失败: {e}")
