from app.model import BaseModel
from tortoise import fields


class EVChargingInfrastructureData(BaseModel):
    title = fields.CharField(max_length=255)
    publish_time = fields.DatetimeField(null=True)
    author = fields.CharField(max_length=255, db_index=True)
    year = fields.IntField(null=True, db_index=True)
    month = fields.IntField(null=True, db_index=True)
    total_charging_facilities = fields.FloatField(null=True)  # 充电设施总数, 单位为万
    public_charging_facilities = fields.FloatField(null=True)  # 公共充电设施总数, 单位为万
    private_charging_facilities = fields.FloatField(null=True)  # 私有充电设施总数, 单位为万
    public_rated_total_power = fields.FloatField(null=True)
    public_average_power = fields.FloatField(null=True)
    private_declared_capacity = fields.FloatField(null=True)
    original_text = fields.TextField(null=True)
    link = fields.CharField(max_length=255)

    class Meta:
        table = 'ev_charging_infrastructure_data'
