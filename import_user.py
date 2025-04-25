from datetime import datetime
from tortoise import run_async
from pymongo import MongoClient

from app.xueqiu.model import XueqiuUser
from common.global_variant import init_db, mongo_uri


async def import_user():
    client = MongoClient(mongo_uri)
    db = client["xueqiu"]
    collection = db["user"]

    await init_db(create_db=False)

    all_user_id = await XueqiuUser.all().values_list('id', flat=True)
    users = []

    while True:
        users = []
        batch = collection.find({'crawl_time': {'$gte': datetime.strptime("2025-04-25T15:00:00", "%Y-%m-%dT%H:%M:%S")}})

        if not batch:
            break

        for item in batch:
            if int(item['id']) not in all_user_id:
                item.pop('crawl_time')
                users.append(XueqiuUser(**item))
        await XueqiuUser.bulk_create(users, ignore_conflicts=True)
        print(f"已导入{len(users)}条数据")


if __name__ == "__main__":
    run_async(import_user())
