import click
from tortoise import Tortoise, run_async
from loguru import logger

from common.global_variant import init_db


async def move_time_field(client, apps):
    """
    移动 create_time update_time 字段到最后行
    :param client:
    :param apps: models
    :return:
    """
    for k, v in apps.get("models").items():
        fields: dict = v._meta.fields_db_projection
        last_field = list(fields.keys())[-1]
        table_name = v.Meta.table
        await client.execute_script(
            f"""alter table {table_name} modify create_time datetime(6) NOT NULL DEFAULT
        CURRENT_TIMESTAMP(6) after {last_field} """
        )
        await client.execute_script(
            f"""alter table {table_name} modify update_time datetime(6) NOT NULL DEFAULT
        CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) after create_time """
        )
        logger.success(f"创建 {table_name} 完毕！")


async def init_mysql() -> None:
    await init_db(create_db=False)
    await Tortoise.generate_schemas()
    client = Tortoise.get_connection('default')
    apps = Tortoise.apps
    try:
        await move_time_field(client, apps)
    except:
        pass
    logger.success("Init Mysql Success")


@click.group()
def cli(): ...


@cli.command()
def initdb():
    run_async(init_mysql())
    click.echo('Init Finished Success!')


if __name__ == '__main__':
    cli()
