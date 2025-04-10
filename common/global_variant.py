import httpx
from fake_useragent import UserAgent
from loguru import logger
from tortoise import Tortoise
from common.config_loader import get_config

config = get_config()

proxy_cfg = config.get('proxy')

proxy_url = "http://%(user)s:%(pwd)s@%(proxy)s/" % {
    "user": proxy_cfg.username,
    "pwd": proxy_cfg.password,
    "proxy": proxy_cfg.tunnel,
}

proxies = httpx.Proxy(url=proxy_url)

ua = UserAgent()


async def init_db(create_db=False) -> None:
    mysql_config = config.get('database.mysql')
    if not mysql_config:
        raise Exception('MySQL config load failed.')
    db_uri = f'mysql://{mysql_config.user}:{mysql_config.passwd}@{mysql_config.host}:{mysql_config.port}/{mysql_config.db_name}'
    logger.info(f'db_uri: {db_uri}')
    await Tortoise.init(db_url=db_uri, modules={'models': ["app.xueqiu.model"]}, _create_db=create_db)
