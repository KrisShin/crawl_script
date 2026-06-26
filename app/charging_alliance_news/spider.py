import asyncio
import json
import random
import re
from typing import Dict

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.charging_alliance_news.login import wechat_login
from app.charging_alliance_news.model import ChargingAllianceNews
from common.email_util import send_email
from app.common.LLM_service import call_LLM
from common.repository import BaseRepository
from common.spider_registry import register_spider

repo = BaseRepository(ChargingAllianceNews)

APPMSG_BASE_URL = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"

logs = []

LLM_PROMPT = """
你是一个专门用于解析"电动汽车充电基础设施运行情况"新闻的**JSON转换引擎**。
你的唯一任务是将非结构化文本转换为**严格符合Schema**的JSON数据。

### 🚨 最高优先级禁令 (违反即失败)
1.  **禁止Markdown**：输出**必须**以 `{` 开头，以 `}` 结尾。严禁包含 ```json 或 ``` 标记。
2.  **禁止单位**：所有数值必须是**纯数字**（Float）。
    - ❌ 错误：`"1281.8万"`, `"59.1亿"`, `"31.3%"`
    - ✅ 正确：`1281.8`, `59.1`, `31.3`
3.  **禁止多余字段**：**只允许**输出"待提取字段列表"中定义的 Key。严禁自作聪明添加 `top10_regions`, `region_data` 等字段。
4.  **禁止增量混淆**：绝不要把"增量/增加"的数据填入"总量/保有量"字段。

### 字段提取逻辑

**1. 时间定位 (Year/Month)**
   - **Year**: 优先从标题提取。
   - **Month**:
     - 优先从标题提取（如"2025年4月..." -> 4）。
     - **特殊情况**：如果标题只有年份（如"2024年全国..."），请阅读正文 **"1 公共充电基础设施运行情况"** 的第一句话。
     - *示例*："2024年12月比..." -> 则月份为 12。

**2. 关键数值提取 (核心规则)**
   - **`public_charging_facilities` (公共保有量)**
     - 目标：截至当前时间的**累计总数**。
     - 关键词锚点："截至...公共充电桩...万台/万个"。
     - *排除*：不要提取"增加"、"新增"的数字。

   - **`private_charging_facilities` (私人保有量)**
     - 目标：截至当前时间的**累计总数**。
     - *陷阱警示*：很多文章只提到"随车配建私人充电桩**增量**为..."。如果你只找到了"增量"，**请将保有量字段填 null**，不要把增量填进去！

   - **`year_NEV_sales` (新能源汽车年度累计销量)**
     - 目标：本年度（1-X月）的**累计销量**。
     - 关键词锚点：文章末尾"充电基础设施与电动汽车对比情况"章节。
     - 匹配逻辑：找 "1-X月...新能源汽车销量...万辆"。即便原文说是"1-5月"，也提取该数字作为年度累计值。

**3. 增量字段 (Increase)**
   - 仅提取明确带有"增加"、"新增"、"增量"描述的数字。

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


def _build_params(creds: Dict[str, str]) -> dict:
    """Build URL query params from in-memory credentials."""
    return {
        "sub": "list",
        "search_field": None,
        "begin": 0,
        "count": "5",
        "query": "",
        "fakeid": creds["fakeid"],
        "type": "101_1",
        "free_publish_type": "1",
        "sub_action": "list_ex",
        "fingerprint": creds["fingerprint"],
        "token": creds["token"],
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
    }


def extract_article_text(html_content):
    """从微信文章 HTML 中提取正文文本"""
    try:
        soup = BeautifulSoup(html_content, "lxml")
        content_div = soup.find("div", id="js_content")
        if not content_div:
            logger.warning("未找到 id='js_content' 的正文容器")
            return ""

        for script in content_div(["script", "style"]):
            script.extract()

        lines = [t.strip() for t in content_div.stripped_strings if t.strip()]
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"解析 HTML 出错: {e}")
        return ""


async def parse_page(title: str, article_url: str):
    try:
        logger.info(f"正在抓取文章: {article_url}")
        logs.append(f"正在抓取文章: {article_url}")

        response = httpx.get(
            article_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
            },
            timeout=10,
        )

        if response.status_code != 200:
            logger.error(f"请求文章失败, 状态码: {response.status_code}")
            logs.append(f"请求文章失败, 状态码: {response.status_code}")
            return

        text_content = extract_article_text(response.text)
        if not text_content:
            logger.warning("未能提取到正文内容")
            logs.append("未能提取到正文内容")
            return

        logger.info("正在调用 DeepSeek 模型提取数据...")
        logs.append("正在调用 DeepSeek 模型提取数据...")
        try:
            resp_json = await call_LLM(text_content, LLM_PROMPT)

            defaults_data = {
                **resp_json,
                "title": title,
                "link": article_url,
                "origin_text": text_content,
                "digest": text_content[:200] if text_content else "",
            }

            pattern = r"(\d{4})年(?:(\d{1,2})月)?"
            match = re.search(pattern, defaults_data.get("title"))
            year = match.group(1)
            month = match.group(2) or 12

            news_data, created = await repo.get_or_create(
                year=year,
                month=month,
                defaults=defaults_data,
            )

            if created:
                logger.success(f"新增数据: {news_data.year}年{news_data.month}月")
                logs.append(f"新增数据: {news_data.year}年{news_data.month}月")
            else:
                logger.info(f"数据已存在: {news_data.year}年{news_data.month}月")
                logs.append(f"数据已存在: {news_data.year}年{news_data.month}月")

            for key, value in resp_json.items():
                if hasattr(news_data, key):
                    setattr(news_data, key, value)
                else:
                    logger.debug(f"忽略模型中不存在的字段: {key}")

            await repo.save(news_data)
            logger.success(f"数据提取并保存成功! 年份: {news_data.year}, 月份: {news_data.month}")
            logs.append(f"数据提取并保存成功! 年份: {news_data.year}, 月份: {news_data.month}")

        except Exception as e:
            logger.error(f"大模型提取或保存数据失败: {e}")
            logs.append(f"大模型提取或保存数据失败: {e}")

    except Exception as e:
        logger.error(f"抓取文章发生异常: {e}")
        logs.append(f"抓取文章发生异常: {e}")


async def parse_list(begin: int, creds: Dict[str, str], client: httpx.AsyncClient):
    params = _build_params(creds)
    headers = {"Cookie": creds["cookie"]}

    while True:
        logger.info(f"start crawling begin: {begin}")
        logs.append(f"start crawling begin: {begin}")
        params["begin"] = begin

        response = await client.get(APPMSG_BASE_URL, params=params, headers=headers, timeout=None)
        await asyncio.sleep(random.randint(1, 3))

        if response.status_code != 200:
            await asyncio.sleep(3600)
            continue

        data = response.json()
        ret = data["base_resp"]["ret"]
        if ret == 200013:
            logger.warning("流量控制, 停止一小时后尝试")
            logs.append("流量控制, 停止一小时后尝试")
            await asyncio.sleep(3600)
            continue
        elif ret == 200003:
            logger.warning("Cookie过期")
            logs.append("Cookie过期")
            return
        elif ret != 0:
            logger.warning(f"未知错误 ret={ret}, 终止尝试")
            logs.append(f"未知错误 ret={ret}, 终止尝试")
            return

        publish_page = json.loads(data["publish_page"])
        if not publish_page:
            logger.info(f"爬取已完成, 共{begin}条数据")
            logs.append(f"爬取已完成, 共{begin}条数据")
            return

        for pl in publish_page["publish_list"]:
            pi = json.loads(pl["publish_info"])
            for news in pi["appmsgex"]:
                title = news["title"]
                if title.startswith("信息发布") and title.endswith("全国电动汽车充换电基础设施运行情况"):
                    if await repo.exists(link=news["link"]):
                        logger.warning("之前数据已爬取, 结束爬虫")
                        logs.append("之前数据已爬取, 结束爬虫")
                        return
                    await parse_page(title, news["link"])

        begin += 5
        await asyncio.sleep(random.randint(10, 30))


@register_spider("charging_alliance", help="Crawl charging alliance WeChat news")
async def main():
    # 1. Open browser, scan QR, grab credentials
    creds = await wechat_login()

    # 2. Start crawling with those credentials
    begin = 0
    logger.info(f"begin: {begin}")
    logs.append(f"begin: {begin}")
    client = httpx.AsyncClient()
    await parse_list(begin, creds, client)
    await send_email("krisshin@88.com", "充电联盟爬虫结束", "\n".join(logs), False)


async def repair():
    all_news = await repo.model.all().order_by("-year", "-month")
    logger.info(f"repair data, total {len(all_news)}")
    for index, news in enumerate(all_news):
        last_news = all_news[index + 1] if index < len(all_news) - 1 else None
        logger.info(
            f"repairing: {news.year}-{news.month}, "
            f"last: {last_news.year}-{last_news.month} "
            f"year_NEV_sales: {news.year_NEV_sales}"
        )
        if last_news and last_news.year_NEV_sales and news.year_NEV_sales:
            news.NEV_sales = news.year_NEV_sales - last_news.year_NEV_sales
        await repo.save(news)


if __name__ == "__main__":
    asyncio.run(main())
