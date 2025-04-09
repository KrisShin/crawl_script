import argparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def run_spiders(spider_names=None):
    settings = get_project_settings()
    process = CrawlerProcess(settings)

    # 自动发现所有爬虫
    if not spider_names:
        from crawl_script.spiders.snowball.index_spider import SnowballIndexSpider

        spiders = [SnowballIndexSpider]
    else:
        # 根据名称动态加载指定爬虫
        pass

    for spider in spiders:
        process.crawl(spider)

    process.start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--spiders', nargs='+', help='指定运行的爬虫名称')
    args = parser.parse_args()

    run_spiders(args.spiders)
