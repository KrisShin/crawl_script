import time
import random
import httpx
from loguru import logger
from scrapy import Selector

from app.base_spider import BaseSpider
from app.anjuke.model import AnjukeSHCommunity
from common.global_variant import ua


class AnjukeSHCommunitySpider(BaseSpider):
    """雪球组合仓位变动数据爬虫"""

    def __init__(self, client: httpx.AsyncClient, page: int):
        super().__init__(client=client, model=AnjukeSHCommunity)
        self.list_url = "https://shanghai.anjuke.com/community/o4-p%(page)d/"
        self.cookie = "SECKEY_ABVK=6XiiQzTYeIvQnOkpKYEDyToHw7DRmxeD52B9uxMhc3U%3D; BMAP_SECKEY=6XiiQzTYeIvQnOkpKYEDyREGl9DOoqAIpCPTkbbNfqxA37gAWTpL9usAZuiHH8OUdpVeFLBFp0DYMi_nCyFPgrh8P586Ry_CH5bSCIMtkZ7IcQU9v04IGMI6bfZqBpuSUzNgWw97wZWQ_-5Wp6878BCSyqrWcEOeH6WsYqqasMs7Zj2BmA4vY4P-pMcB6_BI; aQQ_ajkguid=DA7643F7-5AC8-47B4-8607-F392953ED21A; sessid=41F935A0-3EF3-40F9-BB5F-553C0FEB8127; ajk-appVersion=; ctid=11; id58=CkwAb2gPOfRcvwU+bEHfAg==; xxzlclientid=49655c5c-7674-42a9-8b76-1745828341642; xxzlxxid=pfmxwFnTkABCGVVi6F3gjdBbaI70CRkqxRPzFj14gjOQ5sUwUCzcY6qVNWsyE7Cs2OoC; twe=2; ajk_member_verify=S%2BQtr7M4uR0BrkPhsMwG4JEgYyJpJoCxs6T5e%2FnRDUk%3D; ajk_member_verify2=MjAxMjU2Nzg5fHl2WmhYT2Z8MQ%3D%3D; fzq_js_anjuke_ershoufang_pc=86484147df97972c27ed3f09db84f4ba_1745828643200_25; obtain_by=2; isp=true; 58tj_uuid=19c943e4-07a2-4baf-b09c-f9e56b3bc352; new_uv=1; als=0; ajk_member_id=201256789; fzq_h=44f6f7d8eb104ede10aee023555795be_1745973795691_f2f69551359043f4a327431208fe1613_1707913195; fzq_js_anjuke_xiaoqu_pc=209075999cb66f5870d14b7c82fe526a_1745973796956_25; ajkAuthTicket=TT=9d41d8663ba7d7cd387b0e6e1c32d597&TS=1745973797852&PBODY=JOgCLKHSIyNr5_Wr1Z2Uh93TxNKMP3RF4zyhrqRBbQVuuSm9eUWLqR2V6sawL9PsUTYhSS1So6W1O9L2Gh7uSnzT8QYsJGtahgrQHb_1UgjrEnKcyzsDqqyE3aI8-JjbgAW4KwI4638uhSrhtqp-Sl-Kv5vsQy12oHUOhKPcSTs&VER=2&CUID=IaMzr4tsYoGtAgumkRBfOBFWXp57TMBP; xxzlbbid=pfmbM3wxMDM0NnwxLjEwLjF8MTc0NTk3Mzc5ODgwMzI0MjgyN3xsWjBZb0tscSs4RWNOK2lydUNrS2doM0lPTG5iOUREN2M0UXVNRHhBY1ZzPXw2YTVhZWNlZWRiZDczNWVmNzIyNGJmYmY4MTg1NmI4OV8xNzQ1OTczNzk3MTc2XzI5MDcyMDljYjcwZjQwM2FiNGNmOTZiYTNlYTZlZmNlXzE3MDc5MTMxOTV8M2RmMDFjZGJiYmQ0MGI3NzE0NmMyY2IyNGZiNmM2OTNfMTc0NTk3Mzc5NzM4OV8yNTY="
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
                                "completion_year": community_info["竣工时间"],
                                "property_years": community_info["产权年限"],
                                "total_households": community_info["总户数"],
                                "total_building_area": community_info["总建面积"],
                                "plot_ratio": community_info["容积率"],
                                "greening_rate": community_info["绿化率"],
                                "building_type": community_info["建筑类型"],
                                "business_circle": community_info["所属商圈"],
                                "unified_heating": community_info["统一供暖"] == "是",
                                "water_electricity_type": community_info["供水供电"],
                                "parking_spaces_info": community_info["停车位"],
                                "property_fee": community_info["物业费"],
                                "parking_fee": community_info["停车费"],
                                "parking_management_fee": community_info["车位管理费"],
                                "property_company": community_info["物业公司"],
                                "address": community_info["小区地址"],
                                "developer": community_info["开发商"],
                            }
                        )
                        await AnjukeSHCommunity.update_or_create(id=community_info["id"], defaults=community_info)
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
            community_list = selector.xpath('//*[@id="__layout"]/div/section/section[3]/section/div[2]/a/@href').getall()
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
            community_key = selector.xpath('//*[@id="__layout"]/div/div[2]/div[3]/div[2]/div[1]/div[2]/div/div/div[1]/text()').getall()
            community_values1 = selector.xpath(
                '//*[@id="__layout"]/div/div[2]/div[3]/div[2]/div[1]/div[2]/div/div/div[2]/div[1]/text()'
            ).getall()
            community_values2 = selector.xpath(
                '//*[@id="__layout"]/div/div[2]/div[3]/div[2]/div[1]/div[2]/div/div[position()>14]/div[2]/text()'
            ).getall()
            resp = dict(
                zip(
                    community_key,
                    [None if "暂无" in v else v.strip() for v in community_values1 + community_values2],
                )
            )
            resp["name"] = selector.xpath("/html/body/div[1]/div/div/div[2]/div[2]/div/h1/text()").getall()[0]
            return resp
        except Exception as e:
            from traceback import print_exc

            print_exc()
            logger.error(f"请求失败: {info_url} {e}")
