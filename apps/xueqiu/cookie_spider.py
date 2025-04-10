import random
import httpx
from loguru import logger
from common.global_variant import ua

cookie_url = 'https://xueqiu.com/?md5__1038='
md5_list = [
    'QqGxcDnDyiitnD05o4%2BrhiDOQf8E40Iidx',
    'QqGxcDnDyiitnD05o4%2BrhiDOQj9AEf2bD',
    'QqGxcDnDyiitnD05o4%2BrhiDOQf3D5Q%3D%3Ddx',
    'QqGxcDnDyiitnD05o4%2BrhiDOQ3%3DrEbLRbD',
    'QqGxcDnDyiitnD05o4%2BrhiDOQ36zionbD',
    'QqGxcDnDyiitnD05o4%2BrhiDOQ3%3D8A%2BD2bD',
]


def main(client: httpx.Client):
    while True:
        md5_str = random.choice(md5_list)
        resp = client.get(
            cookie_url + md5_str, headers={'User-Agent': ua.chrome, 'Host': 'xueqiu.com', 'origin': 'https://xueqiu.com'}, timeout=30
        )  # httpx会自动管理获取的cookie
        cookies = [x for x in resp.headers.raw if b'Set-Cookie' in x]
        if len(cookies) < 3:
            logger.error(f'获取cookie失败')
            continue
        logger.success(f'获取cookie成功: {client.headers.raw}')
        return True


if __name__ == '__main__':
    from common.global_variant import proxies

    with httpx.Client(proxies=proxies) as client:
        main(client)
