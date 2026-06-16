import asyncio
import importlib
import inspect

import click
from loguru import logger

from common.global_variant import init_db
from common.spider_registry import (
    get_spider,
    get_spider_names,
    register_spider,
)

# ---------------------------------------------------------------------------
# Import spider modules so their @register_spider decorators fire.
# ---------------------------------------------------------------------------
_ACTIVE_SPIDER_MODULES = [
    "app.charging_alliance_news.spider",
    "app.nea_news.spider",
    "app.research_report.rmi_spider",
]

for _mod in _ACTIVE_SPIDER_MODULES:
    try:
        importlib.import_module(_mod)
    except Exception as exc:
        logger.warning(f"Skipped spider module {_mod}: {exc}")

# ---------------------------------------------------------------------------
# Register xueqiu spiders — wrapper adapters stay here so xueqiu code is untouched.
# ---------------------------------------------------------------------------
try:
    from app.xueqiu.main import (
        analyze,
        contrib,
        crawl_index,
        crawl_rebalancing,
        crawl_zh,
        crawl_zh_async,
        crawl_zh_history_async,
        crawl_user_async,
    )

    register_spider("index", help="Crawl xueqiu stock index")(crawl_index)
    register_spider("zh_single", help="Crawl xueqiu ZH (single-threaded)")(crawl_zh)
    register_spider("ana", help="Analyze ZH and drawdown")(analyze)

    @register_spider("zh", help="Crawl xueqiu ZH index (async)")
    async def _zh(start_id: int = 100389, end_id: int = 25800000, coroutine_count: int = 30):
        await crawl_zh_async(start_id, end_id, coroutine_count)

    @register_spider("zh_his", help="Crawl xueqiu ZH history (async)")
    async def _zh_his(start_id: int = 105040, end_id: int = 1094677, coroutine_count: int = 5):
        await crawl_zh_history_async(start_id, end_id, coroutine_count)

    @register_spider("user", help="Crawl xueqiu user data (async)")
    async def _user(start_id: int = 0, end_id: int = 500450, coroutine_count: int = 5):
        await crawl_user_async(start_id, end_id, coroutine_count)

    @register_spider("reb", help="Crawl xueqiu ZH rebalancing history")
    async def _reb(start_id: int = 0, end_id: int = 1265067, coroutine_count: int = 5):
        await crawl_rebalancing(start_id, end_id, coroutine_count)

    @register_spider("ctb", help="Calculate portfolio stock contributions")
    async def _ctb(start_id: int = 0, end_id: int = 0, coroutine_count: int = 0):
        await contrib(start_id)

except ImportError as exc:
    logger.warning(f"Xueqiu module not available: {exc}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
@click.command()
@click.argument(
    "spider_name",
    type=click.Choice(get_spider_names(), case_sensitive=False),
    required=False,
)
@click.argument("start_id", type=int, required=False, default=0)
@click.argument("end_id", type=int, required=False, default=0)
@click.argument("coroutine_count", type=int, required=False, default=5)
def run_spider(spider_name, start_id: int, end_id: int, coroutine_count: int):
    """Run a registered spider by name.  Use --help to list available spiders."""
    if spider_name is None:
        click.echo(run_spider.get_help(click.Context(run_spider)))
        return

    entry = get_spider(spider_name)
    if entry is None:
        logger.error(f"Unknown spider: {spider_name}")
        return

    sig = inspect.signature(entry.handler)
    kwargs = {}
    for param_name in ("start_id", "end_id", "coroutine_count"):
        if param_name in sig.parameters:
            kwargs[param_name] = locals()[param_name]

    # Run init + spider in a single event loop so Tortoise connections survive.
    async def _run():
        await init_db(create_db=False)
        logger.success("Connect Mysql Success")
        await entry.handler(**kwargs)

    asyncio.run(_run())


if __name__ == "__main__":
    run_spider()
