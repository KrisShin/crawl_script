from tortoise import fields
from app.model import BaseModel


class XueqiuCropIndex(BaseModel):
    """雪球公司指数模型"""

    symbol = fields.CharField(null=False, max_length=64, description='股票代码', db_index=True)
    code = fields.CharField(null=True, max_length=32, description='公司代码', db_index=True)
    name = fields.CharField(null=True, max_length=1024, description='公司名')
    percent = fields.FloatField(null=True, description='涨跌幅')
    current = fields.FloatField(null=True, description='当前价')
    current_year_percent = fields.FloatField(null=True, description='年初至今涨跌百分比')
    market_capital = fields.FloatField(null=True, description='市值')
    amount = fields.FloatField(null=True, description='成交额')
    chg = fields.FloatField(null=True, description='涨跌额')
    volume = fields.FloatField(null=True, description='成交量')
    volume_ratio = fields.FloatField(null=True, description='成交量占比')
    turnover_rate = fields.FloatField(null=True, description='换手率')
    index_type = fields.CharField(max_length=16, null=False, db_index=True, description='指数榜单')

    class Meta:
        table = 'xueqiu_corp_index'
        # unique_together = ('symbol', 'index_type')


class XueqiuZHIndex(BaseModel):
    """雪球组合指数模型"""

    annualized_gain_rate = fields.FloatField(null=True, description='年化收益率')
    daily_gain = fields.FloatField(null=True, description='日收益')
    draw_down = fields.FloatField(null=True, description='提取')
    flowing = fields.BooleanField(null=True, description='流动性')
    market = fields.CharField(null=True, max_length=8, description='市场')
    monthly_gain = fields.FloatField(null=True, description='月收益')
    name = fields.CharField(null=True, max_length=128, description='组合名称')
    net_value = fields.FloatField(null=True, description='当前净值')
    owner_id = fields.BigIntField(null=False, description='创建者_id')
    owner_name = fields.CharField(null=True, max_length=128, description='创建者名字')
    stock_symbol = fields.CharField(null=True, max_length=128, description='股票代号')
    stock_symbol_name = fields.CharField(max_length=128, null=False, db_index=True, description='股票名称')
    symbol = fields.CharField(max_length=16, null=False, db_index=True, description='组合代号')
    total_gain = fields.FloatField(null=True, db_index=True, description='总收益')
    weight = fields.FloatField(null=True, db_index=True, description='权重')

    class Meta:
        table = 'xueqiu_zh_index'


'''
{
  "annualized_gain_rate": 82.2,
  "daily_gain": 1.29,
  "draw_down": null,
  "flowing": false,
  "id": 642832,
  "market": "cn",
  "monthly_gain": 1.31,
  "name": "永远的价值投资",
  "net_value": 8.9609,
  "owner_id": 9522147036,
  "owner_name": "ZZ贵州茅台价值之道",
  "stock_symbol": "SH600519",
  "stock_symbol_name": "贵州茅台",
  "symbol": "ZH642930",
  "total_gain": 796.09,
  "weight": null
}
'''
