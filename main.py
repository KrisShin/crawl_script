from loguru import logger
from tortoise import run_async
from common.global_variant import init_db


def main(db_type: str):
    match db_type:
        case 'mysql':
            run_async(init_db(create_db=False))
            logger.success("Init Mysql Success")


if __name__ == '__main__':
    main('mysql')
    from app.xueqiu.main import main as xueqiu_spider

    xueqiu_spider()
