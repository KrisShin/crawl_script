from datetime import datetime, time
import random
import httpx
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

from app.base_spider import BaseSpider
from app.xueqiu.model import XueqiuRebalancing
from common.global_variant import ua, mongo_uri, mongo_config, symbol_all_list

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
cookie = 's=bq1204xe6n; cookiesu=901744357221250; device_id=501dedaaad2e70097fc5676dfdfe7d3b; bid=a66cc8d3abe54e222cd5a22d628e6bbe_m9ch9y7z; __utmz=1.1744357264.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); Hm_lvt_1db88642e346389874251b5a1eded6e3=1743390251,1744007459,1744939100; HMACCOUNT=9605A34B28A1FB47; __utma=1.1099311988.1744357264.1744679568.1744947738.5; __utmc=1; acw_tc=1a0c640617449569267033201e007da583c8f86436221b0abbef18a2843210; remember=1; xq_a_token=8a371dd6b90dff075cd37cfeb58498dd461cc62c; xqat=8a371dd6b90dff075cd37cfeb58498dd461cc62c; xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOjMzMTkwMTQ3MjIsImlzcyI6InVjIiwiZXhwIjoxNzQ3NTQ5NTU4LCJjdG0iOjE3NDQ5NTc1NTgxODYsImNpZCI6ImQ5ZDBuNEFadXAifQ.XfyJfO0rqyon8BtPAY0yGZZb3PIq5oXXSFakiL9f98zlCN0eXankXCcV8SegahC2nXEnjJunLNfObXVW-5L68Rqpewdh0AVvLPhPRONS7poNEFzgg_7CI4AApshvJKJOygkWDxI97jTCKsYwRiSDq8Yu4UXDdtCriXSu-2L2MI-6JQoZodzxaxnUtkgUfWrPlXTYd3UZyEGlEoaAiVlxq9E6rDo1ssYU8T72eYh3PT2MkHANEqPqW9TAm6GPLuDN2C5_ZIr0ajoIiuu1eWvAD5t166swbD6nvzwZEyA6BwURRdLk7G78GbaFiBnbB7ousnIlqayoztfLPTqHnUqHRA; xq_r_token=ac5a6d400e1dc47eafcb90d833d5f7bde5be8e88; xq_is_login=1; u=3319014722; is_overseas=0; Hm_lpvt_1db88642e346389874251b5a1eded6e3=1744957563; .thumbcache_f24b8bbe5a5934237bbc0eda20c1b6e7=ldGEGhzBMZKKbPi3G5geQoexjhSmLxkhnUZh2RqGxWZGlXDNNfWXY8Uz4OvZs8YF5vgAfG+bLFhL1vP1mjf37Q%3D%3D; ssxmod_itna=WqUxRQG=Yri7G7DgQDpgQDCGD8fCDXDUL4iQGgDYq7=GFQDCx7K7wWiY4tt34PqoCGD32DCDBq+rDSxD6FDK4GTG82oqD70pGD9xiImnDxoqrmDkR1ErQ00rRqt9fwRgClzlCStB2oqeD8RxDKqGmD0=DAL4D7qmQDxGGm4GwDGoD34DiDDPoxDtikj4D7OT32muDLir58CTDmf4eTE4DmqHDnxaro1uDh7TDGSFDzMWDf42TD644xY=DQqS3bOTDj4yTG97exYpwfn7wxBjsTmi7lQnrLBkiQGqZ4rd=DrtYmx+Q44dObiYmytm0/0b5+HKm5FiqPQDtDhFK+FKKmKb4+YYBGQzBBQ5SimSGWlmq4mGztb4R0rQRH0bHzoej5tnxN3ix/vxzBDmGe4BxCTKx+DD; ssxmod_itna2=WqUxRQG=Yri7G7DgQDpgQDCGD8fCDXDUL4iQGgDYq7=GFQDCx7K7wWiY4tt34PqoCGD32DiDG+AQCdmx7POOQBQhQDlc44WvCDDwcUtvR2DB6KBmxL90iRmDMu0R/I1SlSTCIPSDjKY7XvAqLx9TdYGiK4j32ZRDfXBBEFmgEnj3qt9MDAGkG0febhjbIEzoiOGq+etebT6fcj8cbuRScRzONqIMfi=id7VciOlTL3vdxKLnEzVTiAG7=ALpN/mrSiqUj08qAKERT0oF4un8xBR3nWg7=Oh7346M0=hayj99f=kr4AUR6q=vR7GMBm=jKqxXAhpQnNTgXcmhxPXCpw0AxAmL4BeYY0VeASpLviQs22B6jF23AAIOPtgr5vijCgPTIrj0hWt2BnKAntl6viKv122GevveNs8ovmfnxj6W=PS2FDoEbak9+F=5sRILRa3WAIO0AlvEm3E2XvS5/APCfXwcxk9hDc48FdzOA3ouKxmh4dC80z8P4R2dtEEgiF/fP+F349G1PSKuLtIoVWU22Ax4zmGhnrvemWKeUYxtyY6D8+UEeatNyheDoFcKi28ehT7vG9npXn8kurC5T4lX8V8syIoD4inpmXCqGq10w4WGU7fILCpXmfdD'


class XueqiuZHRebalancingSpider(BaseSpider):
    """雪球组合仓位变动数据爬虫"""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(client=client, model=XueqiuRebalancing)
        self.base_url = 'https://xueqiu.com/cubes/rebalancing/history.json?cube_symbol=%s&count=50&page=%d&md5__1038=%s'

    async def crawl(self, zh_index: int, max_index: int):
        rebalancing_list = []
        while zh_index < max_index:
            page = 1
            max_page = 9999999
            while page <= max_page:
                index_url = self.base_url % (symbol_all_list[zh_index], page, random.choice(md5_list))
                try:
                    resp = await self.client.get(index_url, headers={'User-Agent': ua.random}, timeout=30)
                    if resp.status_code != 200:
                        logger.error(
                            f'获取组合调仓数据失败: index:{zh_index}, zh_id:{symbol_all_list[zh_index]} code: {resp.status_code}, {resp.text}'
                        )
                        continue
                    data = resp.json()
                    if page == 1:
                        max_page = data['max_page']

                    rebalancing_list.extend(data['list'])
                    # with open(f'xueqiu_zh_id', 'a') as f:
                    #     f.write(f'ZH{zh_id}\n')
                    logger.success(f'获取组合调仓数据成功: index: {zh_index} ZHID:{symbol_all_list[zh_index]}, crawled:{len(data["list"])}')
                    page += 1
                except Exception as e:
                    logger.error(f'请求失败: {e}')
                    continue
                time.sleep(random.randint(3, 8))
            zh_index += 1
        # await self.save(history_list)
        # logger.success(f'获取组合历史数据完成')
        if rebalancing_list:
            try:
                mongo_client = AsyncIOMotorClient(mongo_uri)
                db = mongo_client[mongo_config.db_name]
                collection = db["zh_rebalancing"]
                update_time = datetime.now()
                # 构建批量操作列表
                operations = [
                    UpdateOne(
                        {"id": item["id"]},  # 查询条件，确保 id 唯一
                        {"$set": {**item, "crawl_time": update_time}},  # 更新内容
                        upsert=True,  # 如果不存在则插入
                    )
                    for item in rebalancing_list
                ]
                # 批量执行操作
                if operations:
                    result = await collection.bulk_write(operations, ordered=False)
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
