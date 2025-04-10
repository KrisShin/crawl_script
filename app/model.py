from tortoise import fields, models


class BaseModel(models.Model):
    id = fields.BigIntField(primary_key=True)
    create_time = fields.DatetimeField(auto_now_add=True)
    update_time = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True
