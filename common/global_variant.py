import httpx
from fake_useragent import UserAgent
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
