import asyncio
import json
import random
import re
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

LLM_PROMPT = """
你是一个专门用于解析“电动汽车充电基础设施运行情况”新闻的**JSON转换引擎**。
你的唯一任务是将非结构化文本转换为**严格符合Schema**的JSON数据。

### 🚨 最高优先级禁令 (违反即失败)
1.  **禁止Markdown**：输出**必须**以 `{` 开头，以 `}` 结尾。严禁包含 ```json 或 ``` 标记。
2.  **禁止单位**：所有数值必须是**纯数字**（Float）。
    - ❌ 错误：`"1281.8万"`, `"59.1亿"`, `"31.3%"`
    - ✅ 正确：`1281.8`, `59.1`, `31.3`
3.  **禁止多余字段**：**只允许**输出“待提取字段列表”中定义的 Key。严禁自作聪明添加 `top10_regions`, `region_data` 等字段。
4.  **禁止增量混淆**：绝不要把“增量/增加”的数据填入“总量/保有量”字段。

### 字段提取逻辑

**1. 时间定位 (Year/Month)**
   - **Year**: 优先从标题提取。
   - **Month**:
     - 优先从标题提取（如“2025年4月...” -> 4）。
     - **特殊情况**：如果标题只有年份（如“2024年全国...”），请阅读正文 **“1 公共充电基础设施运行情况”** 的第一句话。
     - *示例*：“2024年12月比...” -> 则月份为 12。

**2. 关键数值提取 (核心规则)**
   - **`public_charging_facilities` (公共保有量)**
     - 目标：截至当前时间的**累计总数**。
     - 关键词锚点：“截至...公共充电桩...万台/万个”。
     - *排除*：不要提取“增加”、“新增”的数字。
   
   - **`private_charging_facilities` (私人保有量)**
     - 目标：截至当前时间的**累计总数**。
     - *陷阱警示*：很多文章只提到“随车配建私人充电桩**增量**为...”。如果你只找到了“增量”，**请将保有量字段填 null**，不要把增量填进去！

   - **`year_NEV_sales` (新能源汽车年度累计销量)**
     - 目标：本年度（1-X月）的**累计销量**。
     - 关键词锚点：文章末尾“充电基础设施与电动汽车对比情况”章节。
     - 匹配逻辑：找 “1-X月...新能源汽车销量...万辆”。即便原文说是“1-5月”，也提取该数字作为年度累计值。

**3. 增量字段 (Increase)**
   - 仅提取明确带有“增加”、“新增”、“增量”描述的数字。

### 待提取字段列表 (JSON Schema)
请严格仅返回包含以下 Key 的 JSON 对象（未找到填 null）：

{
    "total_charging_facilities": null,    // (float) 基础设施累计数量 (万台/万个)
    "public_charging_facilities": null,   // (float) 公共桩累计数量 (万台/万个)
    "private_charging_facilities": null,  // (float) 私人桩累计数量 (万台/万个) [注意：找不到累计值填null，别填增量]
    "public_rated_total_power": null,     // (float) 公共桩额定总功率 (亿千瓦)
    "public_average_power": null,         // (float) 公共桩平均功率 (千瓦)
    "private_declared_capacity": null,    // (float) 私人桩报装容量 (亿千伏安)
    "total_charging_capacity": null,      // (float) 全国充电总电量 (亿度/亿kWh)
    "increase_charging_facilities": null, // (float) [增量] 基础设施增量
    "increase_public_facilities": null,   // (float) [增量] 公共桩增量
    "increase_private_facilities": null,  // (float) [增量] 私人桩增量
    "year_NEV_sales": null                // (float) 本年度/1-X月累计销量 (万辆)
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
            raise Exception('Cookie过期')
        elif data['base_resp']['ret'] != 0:
            # 未知错误, 终止尝试
            raise Exception('Cookie过期')
        publish_page = json.loads(data['publish_page'])
        if not publish_page:
            logger.info(f'爬取已完成, 共{begin}条数据')
            return
        for pl in publish_page['publish_list']:
            pi = json.loads(pl['publish_info'])
            for news in pi['appmsgex']:
                if news['title'].startswith("信息发布") and news['title'].endswith("全国电动汽车充换电基础设施运行情况"):
                    if await ChargingAllianceNews.filter(year=news['year'], month=news['month']).exists():
                        logger.warning('之前数据已爬取, 结束爬虫')
                        await parse_page(news['title'], news['link'])

        begin += 5
        time.sleep(random.randint(10, 30) / 1)


async def main():
    begin = 0
    logger.info(f'begin: {begin}')
    client = httpx.AsyncClient()
    await parse_list(begin, client)


async def repair():
    all_news = await ChargingAllianceNews.all().order_by('-year', '-month')
    logger.info(f'repair data, total {len(all_news)}')
    expected_fields = [
        "total_charging_facilities",
        "public_charging_facilities",
        "private_charging_facilities",
        "public_rated_total_power",
        "public_average_power",
        "private_declared_capacity",
        "total_charging_capacity",
        "increase_charging_facilities",
        "increase_public_facilities",
        "increase_private_facilities",
        "year_NEV_sales",
    ]
    for index, news in enumerate(all_news):
        # try:
        #     parse_json = call_hunyuan(re.sub(r'\s+', '', news.origin_text), LLM_PROMPT, expected_fields)
        # except:
        #     continue
        # logger.info(f'parse json: {parse_json}')
        last_news = all_news[index + 1] if index < len(all_news) - 1 else None
        logger.info(
            f'reparing: {news.year}-{news.month}, last: {last_news.year}-{last_news.month} news_year_NEV_sales: {news.year_NEV_sales}, last_news_year_NEV_sales: {last_news.year_NEV_sales}'
        )
        if last_news and last_news.year_NEV_sales and news.year_NEV_sales:
            news.NEV_sales = news.year_NEV_sales - last_news.year_NEV_sales
        # for key, value in parse_json.items():
        #     org_value = getattr(news, key, None)
        #     if value is not None and value != org_value and hasattr(news, key):
        #         # 如果原数据已经有值，你可以选择覆盖或者保留。这里选择【强制覆盖】以修复错误数据
        #         setattr(news, key, value)
        await news.save()


if __name__ == '__main__':
    asyncio.run(main())
