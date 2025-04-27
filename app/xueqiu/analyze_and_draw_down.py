import asyncio
import json
from collections import defaultdict
from datetime import datetime
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from app.xueqiu.model import XueqiuZHHistory, XueqiuZHIndex
from common.global_variant import mongo_uri, mongo_config

BATCH_SIZE = 500
MAX_WORKERS = 5  # 同时最多处理5个batch
QUEUE_SIZE = 10  # 拉取队列最大长度，避免堆爆

mongo_client = AsyncIOMotorClient(mongo_uri)
db = mongo_client[mongo_config.db_name]
collection = db["analyze"]


def max_drawdown(values):
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        max_dd = max(max_dd, dd)
    return round(max_dd, 6)


async def fetch_batches(start_id, queue: asyncio.Queue):
    """
    不断拉取数据并放入 queue
    """
    current_id = start_id
    while True:
        batch = await XueqiuZHHistory.filter(id__gt=current_id).order_by('id').limit(BATCH_SIZE)
        if not batch:
            await queue.put(None)  # 拉取结束，通知消费者
            break

        await queue.put(batch)
        current_id = batch[-1].id


async def process_batches(queue: asyncio.Queue):
    """
    消费 queue 中的 batch，异步处理
    """
    last_id = 0
    try:
        with open("analyse_last_id.txt", "r") as f:
            last_id = int(f.read())
    except:
        pass

    while True:
        batch = await queue.get()
        if batch is None:
            queue.put_nowait(None)  # 继续传递结束信号给其他worker
            break

        t0 = datetime.now()

        update_tasks = []
        mongo_docs = []
        new_last_id = batch[-1].id

        for record in batch:
            try:
                year_values = defaultdict(list)
                data = json.loads(record.history)
                min_value = float("inf")
                his_len = 0

                for d in data:
                    his_len += 1
                    if "value" in d and isinstance(d["value"], (int, float)):
                        try:
                            date_str = d["date"]
                            value = d["value"]
                            min_value = min(min_value, value)
                            year = datetime.strptime(date_str, "%Y-%m-%d").year
                            year_values[year].append(value)
                        except Exception:
                            continue

                drawdown_by_year = (
                    {str(year): max_drawdown(vals) for year, vals in year_values.items() if len(vals) >= 10} if year_values else None
                )

                if drawdown_by_year:
                    update_tasks.append(
                        XueqiuZHIndex.filter(symbol=record.symbol).update(draw_down=drawdown_by_year)
                    )

                if his_len >= 365 * 3 and min_value >= 1:
                    mongo_docs.append({'symbol': record.symbol})

            except Exception as e:
                logger.warning(f"Parse failed for {record.symbol}: {e}")

        # 并发 update draw_down
        if update_tasks:
            await asyncio.gather(*update_tasks, return_exceptions=True)

        # 异步批量插入 MongoDB
        if mongo_docs:
            try:
                await collection.insert_many(mongo_docs, ordered=False)
            except Exception as e:
                logger.warning(f"Mongo insert_many failed: {e}")

        # 更新 last_id
        last_id = new_last_id
        with open("analyse_last_id.txt", "w") as f:
            f.write(str(last_id))

        t1 = datetime.now()
        logger.success(f"处理完 batch, 批大小: {len(batch)}, 用时: {(t1 - t0).total_seconds():.2f}s, 更新 last_id: {last_id}")


async def get_good_zh_and_draw_down():
    try:
        with open("analyse_last_id.txt", "r") as f:
            last_id = int(f.read())
    except:
        last_id = 0

    queue = asyncio.Queue(maxsize=QUEUE_SIZE)

    producer = asyncio.create_task(fetch_batches(last_id, queue))
    consumers = [asyncio.create_task(process_batches(queue)) for _ in range(MAX_WORKERS)]

    await asyncio.gather(producer, *consumers)

    await mongo_client.close()