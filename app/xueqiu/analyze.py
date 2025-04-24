import json

from loguru import logger
from app.xueqiu.model import XueqiuZHHistory

BATCH_SIZE = 100


async def get_good_zh():

    last_id = 0
    symbols = []
    while True:
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
                    symbols.append(record.symbol)
                logger.info(
                    f"组合:{record.name}-{record.symbol} 的历史数据长度: {his_len}, 最小净值: {min_value}, 符合条件:{'👌🏻' if min_value >= 1 and his_len>365*3 else '🚫'}"
                )

            except Exception as e:
                print(f"Parse failed for {record.symbol}: {e}")
        with open("good_zh.json", "w") as f:
            f.write(json.dumps(symbols, indent=4, ensure_ascii=False))
            logger.success(f"成功写入 {len(symbols)} 条数据到 good_zh.json")
    return symbols
