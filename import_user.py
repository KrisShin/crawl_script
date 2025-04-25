import json
from tortoise import run_async

from app.xueqiu.model import XueqiuUser
from common.global_variant import init_db


async def import_user():
    await init_db(create_db=False)
    with open('./xueqiu.user.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    all_user_id = await XueqiuUser.all().values_list('id', flat=True)
    users = []
    for index, item in enumerate(data):
        if int(item['id']) in all_user_id:
            continue
        # item['verified_infos'] = json.dumps(item['verified_infos'])
        # item['national_network_verify'] = json.dumps(item['national_network_verify'])
        item.pop('crawl_time')
        users.append(XueqiuUser(**item))
        if index % 1000 == 0:
            await XueqiuUser.bulk_create(users, ignore_conflicts=True)
            users = []
            print(f"已导入{index}条数据")
    await XueqiuUser.bulk_create(users, ignore_conflicts=True)
    print(f"已导入{index}条数据")


if __name__ == "__main__":
    run_async(import_user())
