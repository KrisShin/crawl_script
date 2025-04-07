from tortoise import fields, models


class BaseModel(models.Model):
    # id = fields.CharField(pk=True, max_length=32, default=generate_random_id)
    id = fields.BigIntField(primary_key=True, description='唯一主键')
    create_time = fields.DatetimeField(auto_now_add=True, description='创建时间')
    update_time = fields.DatetimeField(auto_now=True, description='更新时间')

    class Meta:
        abstract = True
