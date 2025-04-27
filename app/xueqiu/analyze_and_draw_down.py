import asyncio
import json
from collections import defaultdict
from datetime import datetime
from loguru import logger
from pymongo import MongoClient

from app.xueqiu.model import XueqiuZHHistory, XueqiuZHIndex
from common.global_variant import mongo_uri, mongo_config

BATCH_SIZE = 500


def max_drawdown(values):
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        max_dd = max(max_dd, dd)
    return round(max_dd, 6)


async def get_good_zh_and_draw_down():
    last_id = 0
    try:
        with open("analyse_last_id.txt", "r") as f:
            last_id = int(f.read())
    except:
        pass

    mongo_client = MongoClient(mongo_uri)
    db = mongo_client[mongo_config.db_name]
    collection = db["analyze"]

    batch = await XueqiuZHHistory.filter(id__gt=last_id).order_by('id').limit(BATCH_SIZE)

    while batch:
        # 提前拉下一批
        next_last_id = batch[-1].id
        next_batch_task = XueqiuZHHistory.filter(id__gt=next_last_id).order_by('id').limit(BATCH_SIZE)

        update_tasks = []
        symbols_to_insert = []

        for record in batch:
            last_id = record.id
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
                    update_tasks.append(XueqiuZHIndex.filter(symbol=record.symbol).update(draw_down=drawdown_by_year))

                if his_len >= 365 * 3 and min_value >= 1:
                    symbols_to_insert.append({'symbol': record.symbol})

                logger.info(
                    f"组合:{record.name}-{record.symbol} 长度: {his_len}, 最小净值: {min_value:.4f}, 符合条件:{'✅' if his_len >= 365 * 3 and min_value >= 1 else '🚫'}"
                )

            except Exception as e:
                logger.warning(f"Parse failed for {record.symbol}: {e}")

        # 批量update
        if update_tasks:
            await asyncio.gather(*update_tasks)

        # 批量插入mongo
        if symbols_to_insert:
            collection.insert_many(symbols_to_insert, ordered=False)

        # 写入 last_id
        with open("analyse_last_id.txt", "w") as f:
            f.write(str(last_id))

        logger.success(f"成功处理 {len(batch)} 条数据, 插入 Mongo {len(symbols_to_insert)} 条, last_id: {last_id}")

        # 等待下一批
        batch = await next_batch_task

    mongo_client.close()
