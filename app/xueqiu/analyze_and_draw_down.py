import asyncio
from tortoise.transactions import in_transaction
from tqdm.asyncio import tqdm
import json
from collections import defaultdict
from datetime import datetime
from loguru import logger

from app.xueqiu.model import XueqiuZHHistory, XueqiuZHPicked

TOTAL_SYMBOLS_ESTIMATE = 1315693  # 预估总量，for 进度条用
BATCH_SIZE = 1000
MAX_WORKERS = 5
QUEUE_SIZE = 10


def max_drawdown(values):
    if not values:
        return 0.0
    peak = values[0]
    if peak == 0:
        return 0.0
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
            if peak == 0:  # 防止后续也为0
                continue
        dd = (peak - v) / peak if peak != 0 else 0
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


async def fast_batch_update(conn, updates: list):
    """
    极限加速版：原生拼接批量 UPDATE
    updates: [(symbol, draw_down_json), ...]
    """
    if not updates:
        return

    cases = []
    symbols = []
    for symbol, draw_down in updates:
        draw_down_str = json.dumps(draw_down, separators=(',', ':'))
        cases.append(f"WHEN '{symbol}' THEN '{draw_down_str}'")
        symbols.append(f"'{symbol}'")

    sql = f"""
    UPDATE xueqiu_zh_index
    SET draw_down = CASE symbol
        {' '.join(cases)}
    END
    WHERE symbol IN ({','.join(symbols)});
    """
    await conn.execute_query(sql)


async def process_batches(queue: asyncio.Queue, pbar):
    last_id = 0
    try:
        with open("analyse_last_id.txt", "r") as f:
            last_id = int(f.read())
    except:
        pass

    while True:
        batch = await queue.get()
        if batch is None:
            await queue.put(None)
            break

        t0 = datetime.now()

        update_objs = []
        picked_objs = []
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
                    update_objs.append((record.symbol, drawdown_by_year))

                if his_len >= 365 * 3 and min_value >= 1:
                    picked_objs.append(XueqiuZHPicked(symbol=record.symbol))

            except Exception as e:
                logger.warning(f"Parse failed for {record.symbol}: {e}")

        try:
            async with in_transaction() as conn:
                # 极限加速，原生 SQL 批量 update
                await fast_batch_update(conn, update_objs)

                # bulk_create picked
                if picked_objs:
                    await XueqiuZHPicked.bulk_create(picked_objs, batch_size=1000, ignore_conflicts=True, using_db=conn)

        except Exception as e:
            logger.warning(f"事务处理异常（已忽略）, error: {e}")

        last_id = new_last_id
        with open("analyse_last_id.txt", "w") as f:
            f.write(str(last_id))

        t1 = datetime.now()
        logger.success(f"事务处理完 batch, 批大小: {len(batch)}, 用时: {(t1 - t0).total_seconds():.2f}s, 更新 last_id: {last_id}")

        pbar.update(len(batch))  # 更新进度条


async def get_good_zh_and_draw_down():
    try:
        with open("analyse_last_id.txt", "r") as f:
            last_id = int(f.read())
    except:
        last_id = 0

    queue = asyncio.Queue(maxsize=QUEUE_SIZE)

    producer = asyncio.create_task(fetch_batches(last_id, queue))

    # 用 tqdm 包装一下，总数估算值
    async with tqdm(total=TOTAL_SYMBOLS_ESTIMATE, desc="分析组合进度", unit="symbols") as pbar:
        consumers = [asyncio.create_task(process_batches(queue, pbar)) for _ in range(MAX_WORKERS)]
        await asyncio.gather(producer, *consumers)
