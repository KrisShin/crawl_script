import asyncio
from loguru import logger
from common.global_variant import init_db


def main(db_type: str):
    match db_type:
        case 'mysql':
            asyncio.run(init_db(create_db=False))
            logger.success("Init Mysql Success")


if __name__ == '__main__':
    main('mysql')
    from app.xueqiu.main import crawl_index, crawl_zh, crawl_zh_async

    # crawl_zh()
    asyncio.run(crawl_zh_async())
