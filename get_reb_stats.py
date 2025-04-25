import datetime
import time
from loguru import logger
from pymongo import MongoClient
from common.global_variant import mongo_uri


def main():
    client = MongoClient(mongo_uri)
    db = client["xueqiu"]

    # 计算昨天的时间窗口
    today = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today = today - datetime.timedelta(days=3)
    yesterday = today - datetime.timedelta(days=1)

    # 1. 昨天新增 symbol 去重数
    daily_symbols = db.zh_rebalancing.distinct("symbol", {"crawl_time": {"$gte": yesterday, "$lt": today}})
    daily_count = len(daily_symbols)

    # 2. 总 symbol 去重数（至今所有）
    all_symbols = db.zh_rebalancing.aggregate([{"$group": {"_id": "$symbol"}}, {"$count": "totalCount"}], allowDiskUse=True)
    total_count = next(all_symbols, {}).get("totalCount", 0)

    # 3. 写入 symbol_stats
    db.symbol_stats.update_one(
        {"date": yesterday.strftime("%Y-%m-%d")},
        {"$set": {"dailyCount": daily_count, "totalCount": total_count, "updatedAt": datetime.datetime.now(datetime.timezone.utc)}},
        upsert=True,
    )
    logger.success("统计完成")


if __name__ == "__main__":
    main()
    # while True:
    #     if datetime.datetime.now().hour < 1:
    #         main()
    #     else:
    #         logger.info("当前时间大于1点，跳过本次统计")
    #         time.sleep(3599)  # 每小时检查一次
