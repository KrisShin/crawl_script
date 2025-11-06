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
import oss2  # <-- 新增

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

oss_bucket: oss2.Bucket = None
OSS_CONFIG = {}
DELETE_LOCAL_AFTER_UPLOAD = False  # 默认值

logger.add("scraper.log", rotation="10 MB", encoding="utf-8")
# --- 爬虫核心功能 ---


def init_oss_client():
    """
    (同步) 初始化 OSS 客户端，使用 oss2
    """
    global oss_bucket, OSS_CONFIG, DELETE_LOCAL_AFTER_UPLOAD
    logger.info("正在初始化 OSS 客户端 (使用 oss2)...")
    try:
        cfg = get_config()
        OSS_CONFIG['access_key_id'] = cfg.oss.alibaba_cloud_access_key_id
        OSS_CONFIG['access_key_secret'] = cfg.oss.alibaba_cloud_access_key_secret
        OSS_CONFIG['endpoint'] = cfg.oss.endpoint
        OSS_CONFIG['bucket_name'] = cfg.oss.bucket_name

        DELETE_LOCAL_AFTER_UPLOAD = cfg.get('delete_local_after_upload', False)

        # 3. 按照 oss2 的方式初始化 Auth 和 Bucket
        auth = oss2.Auth(OSS_CONFIG['access_key_id'], OSS_CONFIG['access_key_secret'])

        # 增加连接池和超时设置
        service = oss2.Service(auth, OSS_CONFIG['endpoint'], connect_timeout=30)

        # Bucket 对象是线程安全的
        oss_bucket = oss2.Bucket(auth, OSS_CONFIG['endpoint'], OSS_CONFIG['bucket_name'], connect_timeout=30)  # 增加超时

        # 验证配置是否正确
        try:
            oss_bucket.get_bucket_info()
            logger.info(f"OSS 客户端初始化成功。Bucket: {OSS_CONFIG['bucket_name']}, Endpoint: {OSS_CONFIG['endpoint']}")
        except oss2.exceptions.OssError as e:
            logger.error(f"OSS 认证或连接失败: {e}")
            raise

    except Exception as e:
        logger.error(f"OSS 客户端初始化失败: {e}")
        raise


async def upload_to_oss(local_filepath: Path, oss_key: str) -> str | None:
    """
    (异步-包装) 使用 oss2.resumable_upload 上传文件并返回公共 URL
    """
    global oss_bucket, OSS_CONFIG
    if not oss_bucket:
        logger.warning("OSS 客户端 (oss_bucket) 未初始化，跳过上传。")
        return None

    try:
        logger.info(f"正在断点续传 {local_filepath} 到 OSS (Key: {oss_key})...")

        # 1. (关键) 异步执行同步的 oss2.resumable_upload
        def _sync_upload():
            # 参照您的示例，使用 resumable_upload
            # 它会自动处理分片、重试、断点续传
            # multipart_threshold=10MB, part_size=5MB, 3 threads
            result = oss2.resumable_upload(
                oss_bucket,
                oss_key,
                str(local_filepath),
                multipart_threshold=1024 * 1024 * 10,  # 超过 10MB 自动分片
                part_size=1024 * 1024 * 5,  # 每个分片 5MB
                num_threads=3,  # 3 个线程并发上传
            )
            # 成功后返回 ETag
            return result.etag

        etag = await asyncio.to_thread(_sync_upload)

        # 2. 检查上传结果
        if etag:
            logger.info(f"上传成功: {oss_key}, ETag: {etag}")

            # 3. (关键) 构建对外下载链接
            # 注意: URL 拼接需要处理 oss_key (特别是 Windows 上的 \ 替换为 /)
            public_url = f"https://{OSS_CONFIG['bucket_name']}.{OSS_CONFIG['endpoint']}/{oss_key.replace(os.path.sep, '/')}"

            # 4. (可选) 删除本地文件
            if DELETE_LOCAL_AFTER_UPLOAD:
                try:
                    await asyncio.to_thread(os.remove, local_filepath)
                    logger.info(f"已删除本地文件: {local_filepath}")
                except Exception as e:
                    logger.warning(f"删除本地文件失败 {local_filepath}: {e}")

            return public_url
        else:
            # 理论上 _sync_upload 失败会抛出异常
            logger.error(f"上传失败 {oss_key}: 未返回 ETag。")
            return None

    except oss2.exceptions.OssError as e:
        logger.error(f"OSS SDK 错误 {local_filepath}: {e}")
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
                oss_url = await upload_to_oss(first_local_path, oss_key)

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
                    # TODO:
                    # if article_url in all_link:
                    #     continue

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
