import asyncio
import json
import random
import time
from bs4 import BeautifulSoup
import httpx
from loguru import logger
from app.charging_alliance_news.model import ChargingAllianceNews
from app.common.hunyuan_api import call_hunyuan
from common.global_variant import config

URL_PARAMS = {
    "sub": "list",
    "search_field": None,
    "begin": 0,
    "count": "5",
    "query": "",
    "fakeid": config.charging_alliance.fakeid,
    "type": "101_1",
    "free_publish_type": "1",
    "sub_action": "list_ex",
    "fingerprint": config.charging_alliance.fingerprint,
    "token": config.charging_alliance.token,
    "lang": "zh_CN",
    "f": "json",
    "ajax": "1",
}

HEADERS = {
    'Cookie': config.charging_alliance.COOKIE,
}
BEGIN_FILE_URI = './app/charging_alliance/begin.log'

LLM_PROMPT = """
你是一个专业的数据提取助手。请阅读给定的【新闻文本】，提取电动汽车充换电基础设施的关键数据。

### 核心提取逻辑
请遍历全文，根据以下**字段定义**和**原文常见表述**来定位数据。
**注意：**
1. **区分总量与增量**：
   - 字段名中未包含 `increase` 的，均指**截至统计时间的累计总量（保有量）**。
   - 字段名包含 `increase` 的，指**统计周期内的增量（新增数量）**。
2. **单位对齐**：请严格按照要求的单位（万个、亿千瓦等）提取纯数字。
3. **模糊匹配**：不要死扣“年销量”这种字眼，只要是“本年度内的累计数据”（如1-10月销量）均视为年度数据。

### 字段提取指南
请提取以下字段（如果原文未提及，返回 null）：

1. **基础信息**
   - `year`: 统计年份 (例如 2025)
   - `month`: 统计月份 (例如 10)

2. **保有量/累计总量 (Total/Cumulative)**
   - `total_charging_facilities`: 充电基础设施总数/累计数量。
     - *原文线索*：“充电基础设施（枪）总数”、“全国充电桩累计数量”
     - *目标单位*：万个
   - `public_charging_facilities`: 公共充电设施总数。
     - *原文线索*：“公共充电设施（枪）...万个”、“公共充电桩累计数量”
     - *注意*：**不要**提取成“增量”，找“截至...”开头的数据。
     - *目标单位*：万个
   - `private_charging_facilities`: 私人/随车配建充电设施总数。
     - *原文线索*：“私人充电设施（枪）...万个”、“随车配建充电设施”
     - *目标单位*：万个
   - `public_rated_total_power`: 公共充电桩额定总功率。
     - *原文线索*：“公共充电桩额定总功率”、“总功率达到”
     - *目标单位*：亿千瓦
   - `public_average_power`: 公共充电桩平均功率。
     - *原文线索*：“平均功率约为”
     - *目标单位*：千瓦
   - `private_declared_capacity`: 私人充电设施报装用电容量。
     - *原文线索*：“报装用电容量”
     - *目标单位*：亿千伏安
   - `total_charging_capacity`: 全国充电总电量。
     - *原文线索*：“全国充电总电量”、“充电电量”
     - *目标单位*：亿度

3. **增量/变化情况 (Increase/Growth)**
   - `increase_charging_facilities`: 充电基础设施增量。
     - *原文线索*：“充电基础设施增量”、“同比增加...”
     - *目标单位*：万个
   - `increase_public_facilities`: 公共充电设施增量。
     - *原文线索*：“公共充电设施增量”
     - *目标单位*：万个
   - `increase_private_facilities`: 私人充电设施增量。
     - *原文线索*：“私人充电设施增量”、“随车配建增量”
     - *目标单位*：万个

4. **车辆销售数据 (Sales)**
   - `year_NEV_sales`: 新能源汽车**本年度累计**销量。
     - *原文线索*：“新能源汽车国内销量”、“1-X月新能源汽车销量”
     - *说明*：即使原文说的是“1-10月销量”，也属于本字段（年度累计），请提取该数字。
     - *目标单位*：万辆
   - `NEV_sales`: 新能源汽车**当月**销量。
     - *原文线索*：“本月新能源汽车销量”、“10月新能源汽车销量”
     - *说明*：必须明确是**单月**数据。如果是累计数据请勿填入此字段。
     - *目标单位*：万辆

### 输出格式 (JSON Only)
请直接返回 JSON 字符串，格式如下：
{
    "year": 2025,
    "month": 10,
    "total_charging_facilities": 1864.5,
    "public_charging_facilities": 453.3,
    "private_charging_facilities": 1411.2,
    "public_rated_total_power": 2.03,
    "public_average_power": 44.69,
    "private_declared_capacity": 1.24,
    "total_charging_capacity": 91.1,
    "increase_charging_facilities": 582.7,
    "increase_public_facilities": 95.4,
    "increase_private_facilities": 487.3,
    "year_NEV_sales": null,
    "NEV_sales": null
}
"""


def extract_article_text(html_content):
    """
    从微信文章 HTML 中提取正文文本
    """
    try:
        soup = BeautifulSoup(html_content, 'lxml')

        # 1. 定位正文容器
        # 微信文章的正文通常在 id="js_content" 的 div 中
        content_div = soup.find('div', id='js_content')

        if not content_div:
            logger.warning("未找到 id='js_content' 的正文容器")
            return ""

        # 2. 移除无用的标签 (可选)
        # 比如 script, style 标签，虽然 get_text 通常会忽略它们，但显式移除更安全
        for script in content_div(["script", "style"]):
            script.extract()

        # 3. 提取文本
        # separator='\n' 保证段落之间有换行
        # strip=True 去除首尾空格
        lines = []
        for text in content_div.stripped_strings:
            # 过滤掉一些可能是布局产生的极短无意义字符，或者保留所有
            if text.strip():
                lines.append(text.strip())

        # 4. 拼接结果
        full_text = '\n'.join(lines)
        return full_text

    except Exception as e:
        logger.error(f"解析 HTML 出错: {e}")
        return ""


async def parse_page(title: str, article_url: str):
    """
    请求文章详情页，解析文本，并调用大模型提取数据
    """
    try:
        logger.info(f"正在抓取文章: {article_url}")
        response = httpx.get(
            article_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0'
            },
            timeout=10,
        )

        if response.status_code == 200:
            # 1. 提取纯文本
            text_content = extract_article_text(response.text)
            if not text_content:
                logger.warning("未能提取到正文内容")
                return

            # 2. 调用混元大模型提取数据
            logger.info("正在调用混元模型提取数据...")
            try:
                # 调用 LLM
                resp_json = call_hunyuan(text_content, LLM_PROMPT)

                # 3. 保存数据
                # 创建数据对象
                defaults_data = {
                    **resp_json,
                    'title': title,
                    'link': article_url,
                    'origin_text': text_content,
                    'digest': text_content[:200] if text_content else "",
                }

                # get_or_create 返回的是一个元组 (对象, 是否创建)
                news_data, created = await ChargingAllianceNews.get_or_create(
                    year=resp_json['year'],  # 查询条件 1
                    month=resp_json['month'],  # 查询条件 2
                    defaults=defaults_data,  # 如果没找到，创建新对象时使用的默认值
                )

                if created:
                    logger.success(f"新增数据: {news_data.year}年{news_data.month}月")
                else:
                    logger.info(f"数据已存在: {news_data.year}年{news_data.month}月")

                # 填充 LLM 提取的数据
                # 遍历 JSON 键值对并设置到模型中
                for key, value in resp_json.items():
                    # 确保 key 存在于模型字段中，防止 LLM 幻觉造出不存在的字段报错
                    if hasattr(news_data, key):
                        setattr(news_data, key, value)
                    else:
                        logger.debug(f"忽略模型中不存在的字段: {key}")

                # 特殊逻辑：计算 NEV_sales (当月销量)
                # 如果 LLM 没有提取到当月销量（因为文中可能只有累计），
                # 但你有上个月的累计销量数据，你可以在这里进行二次计算。
                # if news_data.NEV_sales is None and news_data.year_NEV_sales:
                #     last_month_data = await ChargingAllianceNews.get_or_none(year=..., month=...)
                #     if last_month_data:
                #          news_data.NEV_sales = news_data.year_NEV_sales - last_month_data.year_NEV_sales

                # 保存到数据库
                await news_data.save()
                logger.success(f"数据提取并保存成功! 年份: {news_data.year}, 月份: {news_data.month}")

            except Exception as e:
                logger.error(f"大模型提取或保存数据失败: {e}")

        else:
            logger.error(f"请求文章失败, 状态码: {response.status_code}")

    except Exception as e:
        logger.error(f"抓取文章发生异常: {e}")


async def parse_list(begin: int, client: httpx.AsyncClient):
    while True:
        logger.info(f'start crawling begin: {begin}')
        params = URL_PARAMS
        params['begin'] = begin
        response = await client.get(config.charging_alliance.URL, params=URL_PARAMS, headers=HEADERS, timeout=None)
        time.sleep(random.randint(1, 3))
        if response.status_code != 200:
            time.sleep(3600)
            continue
        data = response.json()
        if data['base_resp']['ret'] == 200013:
            # 流量控制, 停止一小时后尝试
            logger.warning('流量控制, 停止一小时后尝试')
            time.sleep(3600)
            continue
        elif data['base_resp']['ret'] == 200003:
            # 没有Cookie或者Cookie过期, 终止尝试
            with open(BEGIN_FILE_URI, 'w') as f:
                f.write(f'{begin}')
            raise Exception('Cookie过期')
        elif data['base_resp']['ret'] != 0:
            # 未知错误, 终止尝试
            with open(BEGIN_FILE_URI, 'w') as f:
                f.write(f'{begin}')
            raise Exception('Cookie过期')
        publish_page = json.loads(data['publish_page'])
        if not publish_page:
            with open(BEGIN_FILE_URI, 'w') as f:
                f.write(f'{begin}')
            logger.info(f'爬取已完成, 共{begin}条数据')
            return
        for pl in publish_page['publish_list']:
            pi = json.loads(pl['publish_info'])
            for news in pi['appmsgex']:
                if news['title'].startswith("信息发布") and news['title'].endswith("全国电动汽车充换电基础设施运行情况"):
                    await parse_page(news['title'], news['link'])

        begin += 5
        time.sleep(random.randint(10, 30) / 1)


async def main():
    begin = 0
    try:
        with open(BEGIN_FILE_URI, 'r') as f:
            begin = int(f.read().strip())
    except:
        pass
    logger.info(f'begin: {begin}')
    client = httpx.AsyncClient()
    await parse_list(begin, client)


if __name__ == '__main__':
    asyncio.run(main())
