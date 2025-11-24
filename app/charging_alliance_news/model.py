from app.model import BaseModel
from tortoise import fields


class ChargingAllianceNews(BaseModel):
    title = fields.CharField(max_length=255)
    link = fields.CharField(max_length=255)
    digest = fields.TextField()
    origin_text = fields.TextField()
    total_charging_facilities = fields.FloatField(null=True, description='充电设施总数, 单位万个')
    public_charging_facilities = fields.FloatField(null=True, description='公共充电设施总数, 单位万个')  # 公共充电设施总数, 单位为万
    private_charging_facilities = fields.FloatField(null=True, description='私人充电设施总数, 单位万个')  # 私有充电设施总数, 单位为万
    public_rated_total_power = fields.FloatField(null=True, description='公共充电桩额定总功率, 单位亿千瓦')
    public_average_power = fields.FloatField(null=True, description='公共充电桩平均功率, 单位千瓦')
    private_declared_capacity = fields.FloatField(null=True, decription='私人充电设施报装用电容量, 单位亿千伏安')
    year = fields.IntField(null=True, db_index=True)
    month = fields.IntField(null=True, db_index=True)

    total_charging_capacity = fields.FloatField(null=True, description='全国充电总电量, 单位亿度')
    increase_charging_facilities = fields.FloatField(null=True, description="充电基础设施增量, 单位万个")
    increase_public_facilities = fields.FloatField(null=True, description='公共充电设施增量, 单位万个')
    increase_private_facilities = fields.FloatField(null=True, description='私人充电设施增量, 单位万个')
    year_NEV_sales = fields.FloatField(null=True, description='新能源汽车国内年销量, 单位万辆')
    NEV_sales = fields.FloatField(
        null=True, description='新能源汽车国内当月销量, 单位万辆'
    )  # TODO: 需要计算, 使用本月年度销量-上月年度销量

    class Meta:
        table = 'charging_alliance_news'
