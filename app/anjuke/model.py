from tortoise import fields
from app.model import BaseModel


class AnjukeSHCommunity(BaseModel):
    """小区信息模型"""

    name = fields.CharField(max_length=128, description="小区名称")
    property_type = fields.CharField(max_length=32, null=True, description="物业类型")  # 住宅
    ownership_type = fields.CharField(max_length=32, null=True, description="权属类别")  # 商品房住宅
    completion_year = fields.IntField(null=True, description="竣工年份")  # 1999
    property_years = fields.IntField(null=True, description="产权年限")  # 70
    total_households = fields.IntField(null=True, description="总户数")  # 762
    total_building_area = fields.FloatField(null=True, description="总建筑面积 (㎡)")  # 70000.0
    plot_ratio = fields.FloatField(null=True, description="容积率")  # 3.00
    greening_rate = fields.FloatField(null=True, description="绿化率 (%)")  # 30.0
    building_type = fields.CharField(max_length=32, null=True, description="建筑类型")  # 小高层高层
    business_circle = fields.CharField(max_length=64, null=True, description="所属商圈")  # 东外滩
    unified_heating = fields.BooleanField(null=True, description="是否统一供暖")  # 否
    water_electricity_type = fields.CharField(max_length=32, null=True, description="供水供电类型")  # 民用
    parking_spaces_info = fields.IntField(max_length=64, null=True, description="停车位数")  # 70(1:0.1)
    property_fee = fields.FloatField(null=True, description="物业费 (元/平米/月)")  # 1.20
    parking_fee = fields.CharField(max_length=128, null=True, description="停车费 (元/月)")  # 150
    parking_management_fee = fields.CharField(max_length=32, null=True, description="车位管理费")  # 暂无
    property_company = fields.CharField(max_length=128, null=True, description="物业公司")  # 上海安得物业管理有限公司
    address = fields.CharField(max_length=256, null=True, description="小区地址")  # 内江路168弄
    developer = fields.CharField(max_length=128, null=True, description="开发商")  # 上海安居置业有限公司

    class Meta:
        table = "anjuke_sh_community"
