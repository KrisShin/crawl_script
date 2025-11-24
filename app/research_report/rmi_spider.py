# run_scraper.py
import asyncio
import os
import httpx
import re
import json
import aiofiles
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from loguru import logger  # <-- 新增
import alibabacloud_oss_v2 as oss

# 导入您的模型和配置加载器
from app.research_report.model import ResearchReport
from common.config_loader import get_config
from common.global_variant import close_db

# --- 配置 ---
BASE_URL = "https://rmi.org.cn"
START_URL = "https://rmi.org.cn/研究成果及洞察/"
DOWNLOAD_DIR = Path("app/research_report/downloads")
MAX_CONCURRENT_REQUESTS = 1  # 并发请求数
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'
}

oss_client: oss.Client = None  # <-- 2. 恢复使用 oss.Client
OSS_CONFIG = {}
DELETE_LOCAL_AFTER_UPLOAD = False

logger.add("scraper.log", rotation="10 MB", encoding="utf-8")
# --- 爬虫核心功能 ---


def init_oss_client():
    """
    (同步) 初始化 OSS 客户端，使用 alibabacloud_oss_v2
    (已修复：使用 region 自动解析内网，不手动设置 endpoint)
    """
    global oss_client, OSS_CONFIG, DELETE_LOCAL_AFTER_UPLOAD
    logger.info("正在初始化 OSS 客户端 (alibabacloud_oss_v2)...")
    try:
        cfg_loader = get_config()

        # 3. 从 config.yaml 加载配置
        OSS_CONFIG['bucket_name'] = cfg_loader.oss.bucket_name
        OSS_CONFIG['public_endpoint'] = cfg_loader.oss.endpoint  # 用于构建 URL
        DELETE_LOCAL_AFTER_UPLOAD = cfg_loader.get('oss.delete_local_after_upload', False)

        # 4. 严格按照您旧代码的逻辑进行认证
        credentials = oss.credentials.StaticCredentialsProvider(
            access_key_id=cfg_loader.oss.alibaba_cloud_access_key_id, access_key_secret=cfg_loader.oss.alibaba_cloud_access_key_secret
        )
        oss_cfg = oss.config.load_default()
        oss_cfg.credentials_provider = credentials

        # 5. (关键) 只设置 region，让 SDK 自动解析 Endpoint
        oss_cfg.region = cfg_loader.oss.region

        # 6. (可选) 增加网络容错 (这仍然是好习惯)
        oss_cfg.connect_timeout_ms = 60000  # 60 秒
        oss_cfg.read_timeout_ms = 120000  # 120 秒
        oss_cfg.max_retries = 5

        oss_client = oss.Client(oss_cfg)

        # 7. 验证连接
        try:
            # 使用 SDK 的内建方法检查
            if not oss_client.is_bucket_exist(OSS_CONFIG['bucket_name']):
                raise Exception(f"OSS Bucket '{OSS_CONFIG['bucket_name']}' 不存在或无权访问。")
            logger.info(f"OSS 客户端初始化成功。Region: {cfg_loader.oss.region} (自动解析Endpoint)")
        except Exception as e:
            logger.error(f"OSS 连接验证失败: {e}", exc_info=True)
            raise

    except Exception as e:
        logger.error(f"OSS 客户端初始化失败: {e}", exc_info=True)
        raise


async def upload_to_oss(local_filepath: Path, oss_key: str) -> str | None:
    """
    (异步-包装) 使用 alibabacloud_oss_v2 的 uploader 上传文件
    (已修复：使用正确的分片参数)
    """
    global oss_client, OSS_CONFIG
    if not oss_client:
        logger.warning("OSS 客户端 (oss_client) 未初始化，跳过上传。")
        return None

    try:
        logger.info(f"正在上传 {local_filepath} 到 OSS (Key: {oss_key})...")

        # 1. (关键) 异步执行同步的 SDK 上传操作
        def _sync_upload():
            # 2. (关键) 按照我们之前的探索，将分片参数传给 uploader()
            uploader = oss_client.uploader(part_size=1024 * 1024 * 5, parallel_num=3)  # 5MB per part

            # 3. 严格按照您旧代码的逻辑调用 upload_file
            result = uploader.upload_file(
                oss.PutObjectRequest(
                    bucket=OSS_CONFIG['bucket_name'],
                    key=oss_key,
                ),
                filepath=str(local_filepath),
            )
            return result

        result = await asyncio.to_thread(_sync_upload)

        # 4. 检查上传结果
        if result.status_code == 200:
            logger.info(f"上传成功: {oss_key}, ETag: {result.etag}")

            # 5. (关键) 使用 config.yaml 中的 public_endpoint 构建公网 URL
            public_url = f"https://{OSS_CONFIG['bucket_name']}.{OSS_CONFIG['public_endpoint']}/{oss_key.replace(os.path.sep, '/')}"

            # 6. (可选) 删除本地文件
            if DELETE_LOCAL_AFTER_UPLOAD:
                try:
                    await asyncio.to_thread(os.remove, local_filepath)
                    logger.info(f"已删除本地文件: {local_filepath}")
                except Exception as e:
                    logger.warning(f"删除本地文件失败 {local_filepath}: {e}")

            return public_url
        else:
            logger.error(f"上传失败 {oss_key}: 状态码 {result.status_code}, Request ID: {result.request_id}")
            return None

    except Exception as e:
        logger.error(f"OSS 上传任务异常 {local_filepath}: {e}", exc_info=True)
        return None


async def fetch_page(client: httpx.AsyncClient, url: str) -> str | None:
    """异步获取单个页面的 HTML 内容"""
    try:
        response = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=20.0)
        response.raise_for_status()  # 如果是 4xx 或 5xx 状态码则抛出异常
        return response.text
    except httpx.RequestError as e:
        print(f"请求失败 {e.request.url}: {e}")
        return None


def clean_filename(filename: str) -> str:
    """清理文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()


async def download_file(client: httpx.AsyncClient, file_url: str, save_path: Path):
    """异步下载单个文件并保存"""
    try:
        # 确保目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)

        async with client.stream('GET', file_url, headers=HEADERS, follow_redirects=True) as response:
            response.raise_for_status()
            async with aiofiles.open(save_path, 'wb') as f:
                async for chunk in response.aiter_bytes():
                    await f.write(chunk)

        print(f"下载成功: {save_path}")
        return str(save_path)  # 返回相对路径字符串
    except httpx.RequestError as e:
        print(f"下载文件失败 {file_url}: {e}")
        return None


async def save_to_db(item_data: dict):
    """将提取的数据存入数据库"""
    try:
        await ResearchReport.update_or_create(
            article_url=item_data['article_url'],
            defaults=dict(
                site=item_data.get('site'),
                title=item_data.get('title'),
                file_url=item_data.get('file_url'),
                download_url=item_data.get('download_url'),
                pulish_date=item_data.get('pulish_date'),
            ),
        )
        print(f"入库成功: {item_data['title']}")
    except Exception as e:
        print(f"入库失败 {item_data['article_url']}: {e}")


async def parse_article_page(client: httpx.AsyncClient, url: str):
    """
    处理单个文章详情页：
    1. 抓取页面
    2. 解析数据
    3. 下载所有附件
    4. 存入数据库
    """
    print(f"正在处理文章: {url}")
    html = await fetch_page(client, url)
    if not html:
        return

    try:
        soup = BeautifulSoup(html, 'lxml')

        title = soup.select_one('h1.insight-post__title')
        publish_date = soup.select_one('time.post_date')

        # 1. 解析数据
        clean_title = clean_filename(title.text) if title else "未知标题"

        # 2. 查找所有附件链接 (基于 2.html)
        original_file_urls = []
        file_links = soup.select('div.insight-download a')
        for link in file_links:
            href = link.get('href')
            if href:
                original_file_urls.append(urljoin(BASE_URL, href))

        # 3. 下载所有附件
        download_tasks = []
        for file_url in original_file_urls:
            original_filename = Path(file_url.split('?')[0]).name  # 去除查询参数后获取文件名
            save_path = DOWNLOAD_DIR / clean_title / original_filename
            download_tasks.append(download_file(client, file_url, save_path))

        local_paths = await asyncio.gather(*download_tasks)
        valid_local_paths = [Path(p) for p in local_paths if p]  # 过滤掉下载失败的 (None)

        oss_url = None
        if valid_local_paths:
            # 只上传第一个下载成功的文件 (因为 download_url 字段是 CharField)
            first_local_path = valid_local_paths[0]

            try:
                # 从本地路径反推出 OSS Key (相对于 DOWNLOAD_DIR)
                # e.g. "报告标题/文件名.pdf"
                oss_key = Path('rmi') / first_local_path.relative_to(DOWNLOAD_DIR).as_posix()

                # 开始上传
                oss_url = await upload_to_oss(first_local_path, str(oss_key))

            except ValueError as e:
                logger.error(f"计算 OSS Key 失败 (路径不在 DOWNLOAD_DIR 内?): {e}")

        # 4. 准备存入数据库
        item_data = {
            'site': 'rmi.org.cn',
            'article_url': url,
            'title': clean_title,
            'pulish_date': publish_date.text.strip()[:-1].replace('年', '-').replace('月', '-') if publish_date else None,
            'file_url': json.dumps(original_file_urls, ensure_ascii=False),  # 存原始链接 JSON
            'download_url': oss_url,  # 存第一个本地路径
        }

        await save_to_db(item_data)

    except Exception as e:
        print(f"解析文章失败 {url}: {e}")


async def main():
    """爬虫主程序"""
    init_oss_client()

    # 创建信号量来控制并发
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    all_link = await ResearchReport.filter().values_list('article_url', flat=True)

    async with httpx.AsyncClient() as client:
        page_num = 1
        current_page_url = f'{START_URL}page/{page_num}/'

        while current_page_url:
            print(f"--- 正在抓取列表页: 第 {page_num} 页 ---")

            list_html = await fetch_page(client, current_page_url)
            if not list_html:
                print("列表页抓取失败，停止。")
                break

            soup = BeautifulSoup(list_html, 'lxml')

            # 1. 提取当前页的所有文章链接 (基于 1.html)
            article_links = soup.select('article.insight h1.insight__title a')
            tasks = []

            for link in article_links:
                href = link.get('href')
                if href:
                    article_url = urljoin(BASE_URL, href)
                    if article_url in all_link:
                        continue

                    # 使用信号量包装任务
                    async def task_wrapper(url):
                        async with semaphore:
                            await parse_article_page(client, url)

                    tasks.append(task_wrapper(article_url))

            # 并发执行当前页的所有文章处理任务
            await asyncio.gather(*tasks)

            # 2. 查找 "下一页" 链接 (基于 1.html)
            next_page_tag = soup.select_one('a.next.page-numbers')
            if next_page_tag and next_page_tag.get('href'):
                current_page_url = urljoin(BASE_URL, next_page_tag['href'])
                page_num += 1
                await asyncio.sleep(1)  # 翻页时稍微等待一下
            else:
                current_page_url = None  # 没有下一页了
                print("--- 所有页面抓取完毕 ---")

    await close_db()


if __name__ == "__main__":
    # 确保 config.yaml 文件在 common/config_loader.py 指定的位置
    asyncio.run(main())
