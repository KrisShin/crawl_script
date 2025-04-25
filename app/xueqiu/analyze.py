import json

from loguru import logger
from pymongo import MongoClient
from app.xueqiu.model import XueqiuZHHistory

from common.global_variant import mongo_uri, mongo_config

BATCH_SIZE = 200


async def get_good_zh():

    last_id = 0
    try:
        with open("analyse_last_id.txt", "r") as f:
            last_id = int(f.read())
    except:
        pass
    while True:
        symbols = []
        batch = await XueqiuZHHistory.filter(id__gt=last_id).order_by('id').limit(BATCH_SIZE)

        if not batch:
            break

        for record in batch:
            last_id = record.id  # 更新分页游标

            try:
                data = json.loads(record.history)
                his_len = len(data)
                if not data or his_len < 365 * 3:
                    continue

                values_f = []
                for d in data:
                    if d.get("value") is not None:
                        values_f.append(d["value"])

                min_value = min(values_f)

                if min_value >= 1:
                    symbols.append({'symbol': record.symbol})
                logger.info(f"组合:{record.name}-{record.symbol} 的历史数据长度: {his_len}, 最小净值: {min_value}, 符合条件:{'👌🏻' if min_value >= 1 and his_len>365*3 else '🚫'}")

            except Exception as e:
                print(f"Parse failed for {record.symbol}: {e}")
        if symbols:
            mongo_client = MongoClient(mongo_uri)
            db = mongo_client[mongo_config.db_name]
            collection = db["analyze"]
            collection.insert_many(symbols, ordered=False)
            mongo_client.close()
        with open("analyse_last_id.txt", "w") as f:
            f.write(str(last_id))
        logger.success(f"成功筛选 {len(symbols)} 条symbol到 MongoDB, last_id: {last_id}")
