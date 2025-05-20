import datetime
import json
import time
from loguru import logger
from pymongo import MongoClient
from common.global_variant import mongo_uri


def main():
    client = MongoClient(mongo_uri)
    db = client["xueqiu"]
    reb = db["zh_rebalancing"]
    stat = db['reb_stat']
    last_index = 0
    with open("last_reb_index", "r") as f:
        last_index = int(f.read().strip())
    all_symbols = None
    with open("symbol_all.json", "r") as f:
        all_symbols = json.load(f)
    for symbol in all_symbols[last_index:]:
        data = reb.find({"symbol": symbol})
        reb_count = len(list(data))
        stat.insert_one({"symbol": symbol, 'count': reb_count})
        logger.success(f"统计 {symbol} 的 rebalance 数量为 {reb_count}")

        last_index += 1
        with open("last_reb_index", "w") as f:
            f.write(str(last_index))


if __name__ == "__main__":
    main()
    # while True:
    #     if datetime.datetime.now().hour < 1:
    #         main()
    #     else:
    #         logger.info("当前时间大于1点，跳过本次统计")
    #         time.sleep(3599)  # 每小时检查一次
