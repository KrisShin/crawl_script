from datetime import datetime
import time
import random
import httpx
from loguru import logger
from pymongo import UpdateOne, MongoClient

from app.base_spider import BaseSpider
from app.xueqiu.model import XueqiuRebalancing
from common.global_variant import ua, mongo_uri, mongo_config, symbol_all_list, user_cookies

md5_list = [
    'euG%3DiIgtY5AIqGNDQ2xBKD%3DO0Qp2eDthTCaq5D',
    '1e761e013c-OidiGI9%3D5IcIlIpF%3D4iri4%3DEVIGL8IyijEnUypsj4rI%3D%2FnHigB%2FAhwtnCbj5DxX%3D%2F0xGIj0Id%3D5gIn%3DxCUIdd5LIodOvIOdIkIR1IIYjIIRIMgIOrs0dGRlr%3DxyIKIjysEI4WITXH3OoIT%3DIBIxgdIGgIpMxJy%3DsoYSWuuxdimB6bGx90rG3RhSIqE%3D%3Ddr5IquIS%3DyI',
    '1e761e013c-OidiGI9%3D5IcIlIpF%3D4iri4%3DEVIGL8IyijEnUypsj4rI%3D%2FnHiwzV5hlQnCbjshts%3DsVdDzQ3RITdsOIriOzI%2FHnssIJds6IYyIUIOWsFuIIguIsisoiIyWpUICKJ%2BI0%3D5RIu%3DpLIF%3Dsna1%3DpNsI50IbHIIoiIAqAPQIxWkGSS%3D%2F5ssMhduGx91ofSRBsIqJ%3D%3Ddr5IquIS%3DyI',
    '1e761e013c-OidiGI9%3D5IcIlIpF%3D4iri4%3DEVIGL8IyijEnUypsj4rI%3D%2FnHiwzV5VjLCbjsh9V5I0Wxq5%3D5qIyds1IzdOk0%3Dyys%2BIJysTIsyIMIrDIIxfIIrIY1IsGIVy5k9KdOnID%3D5pIV%3DjRI4fRLsJIjuIEdsDpIsaIspUYvyIMn6kmhdiIU60jsHX%2F5S%2BMEA0pI9oOsIWdbIyuOI',
    '1e761e013c-qi4iYI9%3DfIA%3D5sriudjFI4iIWI2jIVe4IaIyu5j46j94VRIl5hqgRdUiJktJxSfw%3D%3DkGOSQRITdsOIriOzI%2FHnssIJds6IYyIUIOWsF4IIw1IsisouIyWiUICKJ%2BI0%3D5RIu%3DpLIF%3Dsna1%3DpP4I50IbByIoiIAqANvIx6omcuiuQi4IdWRujyjuxdPwhy3ddSzsQi3z5I%3DI',
    '1e761e013c-OidiGI9%3D5IcIlIpF%3D4iri4%3DEVIGL8IyijEnUypsj4rI%3D%2FnHigB%2FMS%3Duwbjshw%2BQQT4ITSishIpyIaIUysMqdppINIGnIg%3DInIY%3DGE%3DIOH%3DIGIxaIIf%3DlpsK0a3szIEisQIld5rIjAkXIcgyIX%3DO1yI51IOyzMndIZyHRJ4O3u4yPt5QLeG5Lrzi%3DxYidyGs%3Dx4IdipI',
    '1e761e013c-4il%3DtIT%3DYI5x5jslIfjIay%3DAQoImjpiIU%3DjFihzTt5quOjLkvUXXyIlOO01hxrrs%3Di1iMIj0Id%3D5gIn%3DxR9Idd5LIodOvIOdIkIRv%3DIYpIIRIMhIOrV4dGClk%3DxyIKIjysEI4WITj63OoiIseIYTLIJuIySUoPIOPJGi%3D0j%3DIG45PDYf3ajInrXHLvrOyCri9vxOy0pI',
    '1e761e013c-qi4iYI9%3DfIA%3D5sriudjFI4iIWI2jIVe4IaIyu5j46j94VRIl5h4MjI1qV4PbjIUFssjMnUishIpyIaIUysMXdppINIGnIg%3DInIY%3DG4iIOKWIGIx6%3DIffGpsK4K3szIEisQIld5rIj%2FwXIcS%3DIX%3DO19I51IOqzKkdIZ5HP8j5pbs%3DOHJiWi4d4iqS6HjAd%3DSOn5xSdnjsII',
    '1e761e013c-4il%3DtIT%3DYI5x5jslIfjIay%3DAQoImjpiIU%3DjFihzTt5quOjLkvXRv0glXaWWiIG4fWSRITdsOIriOzI%2FinssIJds6IYyIUIOWsFqIIgdIsiso0Iy%2BuAIC1JXI0%3D5RIu%3DpLIF%3Dsnt%2B%3DUaIIX%3DO1CI51IOUQGZIIZUFR0jSPixI%3DX4Y3IpH%3DUxh3XGlyWySLjdUdQxsII',
    '1e761e013c-qi4iYI9%3DfIA%3D5sriudjFI4iIWI2jIVe4IaIyu5j46j94VRIl5h4MjI1qV4PbjIUFssem%3DiDpRITdsOIriOzI%2FBnssIJds6IYyIUIOWsF4IIw2IsisouIyWHUICigjI0%3D5RIu%3DpLIF%3Dshar%3DOojIseIYXnIJuIywq26IOPJGFPu4AujIYp85fIHIFIeIMpTxOOpqd4bxOdupI',
    '1e761e013c-OidiGI9%3D5IcIlIpF%3D4iri4%3DEVIGL8IyijEnUypsj4rI%3D%2FnHiwzV5VjLCbjshw8i54Vq5%3D5qIyds1IzdOkn%3Dyys%2BIJysTIsyIMIrDIIxfIIrIY1IsGIey5kUcdOnID%3D5pIV%3DjRI4wuLsJIdseIYu%3DIJuIykqoAIOPcEiiiqS%3DIfv345QLeG5LrXQ3yszPpOsiuslIp4sII',
    'n4%2BxgD0D9DyAD%3DQGQDCDlhje9MODc77iDQuqcvID',
]


class XueqiuZHRebalancingSpider(BaseSpider):
    """雪球组合仓位变动数据爬虫"""

    def __init__(self, client: httpx.AsyncClient, index: int):
        super().__init__(client=client, model=XueqiuRebalancing)
        self.base_url = 'https://xueqiu.com/cubes/rebalancing/history.json?cube_symbol=%s&count=50&page=%d&md5__1038=%s'
        self.cookie = list(user_cookies.values())[index % 4]

    def crawl(self, zh_index: int, max_index: int):
        rebalancing_list = []
        while zh_index < max_index:
            page = 1
            max_page = 9999999
            update_time = datetime.now()
            while page <= max_page:
                if page > 50:
                    break
                index_url = self.base_url % (symbol_all_list[zh_index], page, random.choice(md5_list))
                try:
                    resp = self.client.get(index_url, headers={'User-Agent': ua.random, 'cookie': self.cookie}, timeout=30)
                    if resp.status_code != 200:
                        logger.error(f'获取组合调仓数据失败: index:{zh_index}, zh_id:{symbol_all_list[zh_index]} code: {resp.status_code}, {resp.text}')
                        time.sleep(120)
                    data = resp.json()
                    if page == 1:
                        max_page = data['maxPage']

                    rebalancing_list.extend([{**item, "crawl_time": update_time, 'symbol': symbol_all_list[zh_index]} for item in data['list']])
                    # with open(f'xueqiu_zh_id', 'a') as f:
                    #     f.write(f'ZH{zh_id}\n')
                    logger.success(f'获取组合调仓数据成功: index: {zh_index} ZHID:{symbol_all_list[zh_index]}, crawled:{len(data["list"])}')
                    page += 1
                except Exception as e:
                    logger.error(f'请求失败: {e}')
                    continue
                time.sleep(1 + random.random() * 3)
            zh_index += 1
        # await self.save(history_list)
        # logger.success(f'获取组合历史数据完成')
        if rebalancing_list:
            try:
                mongo_client = MongoClient(mongo_uri)
                db = mongo_client[mongo_config.db_name]
                collection = db["zh_rebalancing"]
                # 构建批量操作列表
                operations = [
                    UpdateOne(
                        {"id": item["id"]},  # 查询条件，确保 id 唯一
                        {"$set": item},  # 更新内容
                        upsert=True,  # 如果不存在则插入
                    )
                    for item in rebalancing_list
                ]
                # 批量执行操作
                if operations:
                    result = collection.bulk_write(operations, ordered=False)
                    logger.success(f"成功保存 {result.upserted_count}, 更新{ result.modified_count} 条数据到 MongoDB max_id: {max_index}")
                mongo_client.close()
            except Exception as e:
                from traceback import print_exc

                print_exc()
                logger.error(f"保存到 MongoDB 失败: {e} max_id: {max_index}")


if __name__ == '__main__':
    from common.global_variant import proxies

    async def run():
        async with httpx.AsyncClient(proxies=proxies) as client:
            spider = XueqiuZHRebalancingSpider(client)
            await spider.crawl(s_id=100389)

    import asyncio

    asyncio.run(run())
