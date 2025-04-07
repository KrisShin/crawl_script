# import argparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from db_manage.init_mysql import cli


def run_spiders(spider_names=None):
    settings = get_project_settings()
    process = CrawlerProcess(settings)

    # 自动发现所有爬虫
    if not spider_names:
        from spiders.spider1.spiders import example1, example2
        from spiders.spider2.spiders import example3

        spiders = [example1.Example1Spider, example2.Example2Spider, example3.Example3Spider]
    else:
        # 根据名称动态加载指定爬虫
        pass

    for spider in spiders:
        process.crawl(spider)

    process.start()


if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-s', '--spiders', nargs='+', help='指定运行的爬虫名称')
    # args = parser.parse_args()

    # run_spiders(args.spiders)
    cli()
