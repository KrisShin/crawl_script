"""
充电联盟（中国充电联盟）公众号爬虫。

数据来源（2026-08 起，无需登录）：
    微信官方"合集"接口 /mp/appmsgalbum?action=getalbum
    通过 config.yaml 中 charging_alliance.biz / album_id 定位合集；
    翻页获取文章列表 -> 标题正则过滤 -> 检查数据库（已有则结束） -> 抓取正文 -> LLM 提取 -> 入库。

说明：
    - 原 appmsgpublish（MP 后台登录 + 编辑器插入他人文章）方案已被微信封禁，已废弃。
    - 单线程顺序爬取，随机延时控制频率，避免被风控。
"""

import asyncio
import random
import re
from typing import List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.charging_alliance_news.model import ChargingAllianceNews
from app.common.LLM_service import call_LLM
from common.email_util import send_email
from common.global_variant import config
from common.repository import BaseRepository
from common.spider_registry import register_spider

repo = BaseRepository(ChargingAllianceNews)

# 微信"合集"接口: 无需登录即可分页获取公众号文章列表
ALBUM_BASE_URL = "https://mp.weixin.qq.com/mp/appmsgalbum"

# 微信内置浏览器 UA: 免验证、免登录
WECHAT_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "MicroMessenger/8.0.34(0x16082222) NetType/WIFI Language/zh_CN"
)

# 目标标题: "信息发布丨2026年6月全国电动汽车充换电基础设施运行情况"
# 注意: 12月及部分历史标题不带月份(如 "信息发布丨2025年全国..."), 此时 month 默认取 12
TITLE_PATTERN = re.compile(
    r"^信息发布\s*[丨|:：]?\s*(\d{4})年(?:(\d{1,2})月)?全国电动汽车充换电基础设施运行情况$"
)

logs: List[str] = []

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


# ---------------------------------------------------------------------------
# 列表获取（微信合集接口）
# ---------------------------------------------------------------------------
def _build_album_params(begin_msgid: Optional[str] = None, begin_itemidx: Optional[str] = None) -> dict:
    """构造合集接口 URL 参数。__biz / album_id 来自 config.yaml，理论不会变更。"""
    params = {
        "action": "getalbum",
        "__biz": config.charging_alliance.biz,
        "album_id": config.charging_alliance.album_id,
        "count": "10",
        "f": "json",
    }
    if begin_msgid:
        params["begin_msgid"] = begin_msgid
        params["begin_itemidx"] = begin_itemidx
    return params


async def fetch_album_page(
    client: httpx.AsyncClient,
    begin_msgid: Optional[str] = None,
    begin_itemidx: Optional[str] = None,
) -> Tuple[Optional[List[dict]], bool]:
    """
    拉取一页合集文章列表。

    返回: (article_list, has_more)；失败时返回 (None, False)。
    article_list 每项包含: title / url / create_time / msgid / itemidx / pos_num
    """
    params = _build_album_params(begin_msgid, begin_itemidx)
    headers = {"User-Agent": WECHAT_UA}

    for attempt in range(1, 6):
        try:
            response = await client.get(ALBUM_BASE_URL, params=params, headers=headers, timeout=60)
            if response.status_code != 200:
                logger.warning(f"合集接口状态码异常: {response.status_code}, 第{attempt}次重试")
                await asyncio.sleep(random.uniform(2, 5))
                continue

            data = response.json()
            ret = data["base_resp"]["ret"]
            if ret == 200013:
                logger.warning("合集接口流量控制(200013), 暂停 60s 后重试")
                logs.append("合集接口流量控制(200013), 暂停 60s 后重试")
                await asyncio.sleep(60)
                continue
            if ret != 0:
                logger.warning(f"合集接口未知错误 ret={ret}, 终止爬取")
                logs.append(f"合集接口未知错误 ret={ret}, 终止爬取")
                return None, False

            album_resp = data.get("getalbum_resp") or {}
            article_list = album_resp.get("article_list") or []
            has_more = album_resp.get("continue_flag") == "1"
            return article_list, has_more
        except Exception as e:
            logger.warning(f"合集接口请求异常: {e}, 第{attempt}次重试")
            await asyncio.sleep(random.uniform(2, 5))

    return None, False


def _match_target_article(title: str) -> Optional[Tuple[int, int]]:
    """
    匹配目标标题，返回 (year, month)。

    标题通常为 "信息发布丨2026年6月全国电动汽车充换电基础设施运行情况"；
    12月或部分历史标题可能为 "信息发布丨2025年全国电动汽车充换电基础设施运行情况"（不带月份），month 默认 12。
    """
    m = TITLE_PATTERN.match(title)
    if not m:
        return None
    year = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else 12
    return year, month


# ---------------------------------------------------------------------------
# 正文解析 & 入库
# ---------------------------------------------------------------------------
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


async def parse_page(client: httpx.AsyncClient, title: str, article_url: str):
    """抓取单篇文章正文 -> LLM 提取结构化数据 -> 写入数据库。"""
    try:
        logger.info(f"正在抓取文章: {article_url}")
        logs.append(f"正在抓取文章: {article_url}")

        headers = {"User-Agent": WECHAT_UA}
        text_content = ""
        for attempt in range(1, 4):
            try:
                response = await client.get(article_url, headers=headers, timeout=60)
                if response.status_code == 200:
                    text_content = extract_article_text(response.text)
                    if text_content:
                        break
                    logger.warning(f"文章正文为空, 第{attempt}次重试")
                else:
                    logger.warning(f"请求文章失败, 状态码: {response.status_code}, 第{attempt}次重试")
            except Exception as e:
                logger.warning(f"请求文章异常: {e}, 第{attempt}次重试")
            await asyncio.sleep(random.uniform(3, 6) * attempt)

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


# ---------------------------------------------------------------------------
# 主流程: 合集翻页 -> 标题过滤 -> 查库 -> 抓取
# ---------------------------------------------------------------------------
async def parse_list(client: httpx.AsyncClient):
    """
    单线程顺序爬取。

    流程（合集按最新在前排列）:
      翻页获取列表 -> 匹配目标标题 -> 检查数据库:
        - 已存在: 说明该月数据已入库, 更早的文章必然也已处理过, 结束爬虫
        - 不存在: 抓取正文 -> LLM 提取 -> 入库, 然后继续往后翻
    """
    logger.info("开始爬取充电联盟合集文章列表")
    logs.append("开始爬取充电联盟合集文章列表")

    begin_msgid = None
    begin_itemidx = None
    page = 0
    while True:
        page += 1
        logger.info(f"正在翻页: 第 {page} 页 (begin_msgid={begin_msgid}, begin_itemidx={begin_itemidx})")
        logs.append(f"正在翻页: 第 {page} 页 (begin_msgid={begin_msgid}, begin_itemidx={begin_itemidx})")

        article_list, has_more = await fetch_album_page(client, begin_msgid, begin_itemidx)
        if article_list is None:
            logger.error("获取合集列表失败, 终止爬虫")
            logs.append("获取合集列表失败, 终止爬虫")
            return
        if not article_list:
            logger.info("合集无更多文章, 结束爬虫")
            logs.append("合集无更多文章, 结束爬虫")
            return

        for item in article_list:
            title = item.get("title", "")
            url = item.get("url", "")
            match = _match_target_article(title)
            if not match:
                continue

            year, month = match
            logger.info(f"命中目标文章: {title}")
            logs.append(f"命中目标文章: {title}")

            if await repo.exists(year=year, month=month):
                logger.success(f"数据已存在: {year}年{month}月, 结束爬虫")
                logs.append(f"数据已存在: {year}年{month}月, 结束爬虫")
                return

            await parse_page(client, title, url)
            # 单线程 + 随机延时, 控制请求频率
            await asyncio.sleep(random.uniform(3, 6))

        if not has_more:
            logger.info("合集翻页完成, 未发现更多目标文章, 结束爬虫")
            logs.append("合集翻页完成, 未发现更多目标文章, 结束爬虫")
            return

        last = article_list[-1]
        next_msgid = last.get("msgid")
        next_itemidx = last.get("itemidx")
        if next_msgid == begin_msgid:
            logger.warning("翻页游标未前进, 终止爬虫避免死循环")
            logs.append("翻页游标未前进, 终止爬虫避免死循环")
            return
        begin_msgid = next_msgid
        begin_itemidx = next_itemidx

        # 翻页间隔随机延时
        await asyncio.sleep(random.uniform(1.5, 3.5))


@register_spider("charging_alliance", help="Crawl charging alliance WeChat news")
async def main():
    # 不再需要扫码登录, 直接使用微信合集接口
    logger.info("charging_alliance 爬虫启动 (微信合集接口, 无需登录)")
    logs.append("charging_alliance 爬虫启动 (微信合集接口, 无需登录)")

    async with httpx.AsyncClient() as client:
        await parse_list(client)

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