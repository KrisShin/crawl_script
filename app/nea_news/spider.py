from datetime import datetime, timedelta
import json
import time
from typing import Dict, Tuple
import httpx
from urllib.parse import quote
from loguru import logger
from scrapy import Selector

from app.common.hunyuan_api import call_hunyuan
from app.nea_news.model import EVChargingInfrastructureData

URL = 'https://www.nea.gov.cn/was5/web/conwebsite/getNewsFromAllData?callback=jsonpCallback&pageNo=%d&pageSize=10&siteId=11200&keyword=%s&sort=1&isInclude=1&neac=&_=%s'
KEYWORD = '国家能源局发布%d年%d月全国电动汽车充电设施数据'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
    'Host': 'www.nea.gov.cn',
}

LLM_PROMPT = """
请你严格扮演一个数据提取程序。你的任务是从“新闻原文”中提取信息，并严格按照“输出规则”生成一个 JSON 对象。

### 输出规则 (必须严格遵守)

1.  **最终格式：** 你的回答**必须有且仅有**一个 JSON 对象。**绝对不**允许包含 ```json ... ``` 标记、任何注释、任何解释性文字或任何前导/后续文本。
2.  **缺失值：** 如果原文中**未提及**任何一个字段所需的信息，请将该字段的值设为 `null`。
3.  **字段提取与单位换算 (核心)：**

    * `year`: 提取数据的年份 (数字, 例如: 2025)。
    * `month`: 提取数据的月份 (数字, 例如: 8)。
    * `total_charging_facilities`: 提取“充电基础设施（枪）总数”。
        * **单位：** 统一换算成 **"万个"** (浮点数)。
    * `public_charging_facilities`: 提取“公共充电设施（枪）”总数。
        * **单位：** 统一换算成 **"万个"** (浮点数)。
    * `private_charging_facilities`: 提取“私人充电设施（枪）”总数。
        * **单位：** 统一换算成 **"万个"** (浮点数)。
    * `public_rated_total_power`: 提取“公共充电桩额定总功率”。
        * **单位：** 统一换算成 **"亿千瓦"** (浮点数)。
    * `public_average_power`: 提取“公共充电桩平均功率”。
        * **单位：** 统一换算成 **"千瓦"** (浮点数)。
    * `private_declared_capacity`: 提取“私人充电设施报装用电容量”。
        * **单位：** 统一换算成 **"亿千伏安"** (浮点数)。

### 新闻原文

"""


async def parse_news(news: dict, data: EVChargingInfrastructureData):
    url = news['originUrl'][0]
    resp = httpx.get(url, headers=HEADERS, timeout=None)
    if resp.status_code != 200 or not resp.text:
        raise Exception('请求失败', resp.status_code, resp.text)
    selector = Selector(text=resp.text)
    data = data or EVChargingInfrastructureData()
    data.title = selector.xpath('//div[@class="titles"]/text()').get().strip()
    data.publish_time = selector.xpath('//span[@class="times"]/text()').get().strip()[5:]
    data.author = selector.xpath('//span[@class="author"]/text()').get().strip()[3:]
    data.original_text = selector.xpath('//span[@id="detailContent"]/p/text()').get().strip()
    data.link = url
    resp_json = call_hunyuan(data.original_text, LLM_PROMPT)
    for key, value in resp_json.items():
        setattr(data, key, value)
    await data.save()
    logger.success(f'获取 {data.title} 完成✅!!!')


async def parse_search() -> Tuple[Dict, EVChargingInfrastructureData]:
    now = datetime.now()
    now = now.replace(day=1) - timedelta(days=1)
    keyword = KEYWORD % (now.year, now.month)
    keyword = KEYWORD % (2025, 9)  # TODO: 测试用, 建议删除
    headers = HEADERS.copy()
    headers['Referer'] = quote('https://www.nea.gov.cn/search.htm?kw=%s' % keyword, safe=";/?:@&=+$,", encoding="utf-8")
    page = 1
    target_news = None
    data = await EVChargingInfrastructureData.get_or_none(title=keyword)
    while True:
        url = URL % (page, keyword, int(time.time() * 1000))
        encoded_url = quote(url, safe=";/?:@&=+$,", encoding="utf-8")
        resp = httpx.get(encoded_url, headers=headers, timeout=None)
        if resp.status_code != 200 or not resp.text or not resp.text.startswith('jsonpCallback'):
            raise Exception('请求失败', resp.status_code, resp.text)
        json_data = json.loads(resp.text[14:-2])
        target_news = next(filter(lambda news: news['linkTitle'] == keyword, json_data['content']['result']), None)
        if target_news:
            break
        page += 1
        time.sleep(3)
    return target_news, data


async def main():
    news, data = await parse_search()
    if news:
        await parse_news(news, data)


if __name__ == '__main__':
    main()
