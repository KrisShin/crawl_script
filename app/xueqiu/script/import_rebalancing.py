from datetime import datetime
import time
from pymongo import MongoClient

from app.xueqiu.model import XueqiuRebalancing
from common.global_variant import init_db, mongo_uri

BATCH_SIZE = 500


async def import_reb():
    client = MongoClient(mongo_uri)
    db = client["xueqiu"]
    collection = db["zh_rebalancing"]
    start_time = datetime.strptime("2025-04-18T00:00:00", "%Y-%m-%dT%H:%M:%S")
    end_time = datetime.strptime("2025-04-19T00:00:00", "%Y-%m-%dT%H:%M:%S")

    await init_db(create_db=False)

    rebs = []
    skip_count = 0
    last_id = 0
    query = {'crawl_time': {'$gte': start_time, '$lt': end_time}}
    total = collection.count_documents(query)

    while True:
        rebs = []
        query_copy = query.copy()
        if last_id:
            query_copy['id'] = {'$gt': last_id}

        t1 = time.time()
        batch = collection.find(query_copy).sort({'id': 1}).batch_size(BATCH_SIZE)
        t2 = time.time()

        list_batch = list(batch)
        t3 = time.time()
        if not list_batch:
            break

        for item in list_batch:
            rebs.append(XueqiuRebalancing(**item))
        t4 = time.time()
        if rebs:
            await XueqiuRebalancing.bulk_create(rebs, ignore_conflicts=True)
            len_rebs = len(rebs)
            skip_count += len_rebs
        t5 = time.time()
        last_id = list_batch[-1]['id']
        print(f"本次导入{len_rebs}条数据, 进度{skip_count}/{total}\n\t用时: 查询:{t2-t1}s 解析:{t3-t2}s 遍历:{t4-t3}s 保存:{t5-t4}s")


if __name__ == "__main__":
    from tortoise import run_async

    run_async(import_reb())
