from tortoise import fields
from app.model import BaseModel


class SnowBallIndex(BaseModel):
    """company model"""

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
        table = 'snowball_index'
        # unique_together = ('symbol', 'index_type')


'''
{
  "symbol": "AREB",  // 股票代码
  "net_profit_cagr": 16.73625974199162,
  "north_net_inflow": null,
  "ps": 0.187147209078715,
  "type": 0,
  "percent": 342.96,  // 涨跌幅
  "has_follow": false,
  "tick_size": 0.01,
  "pb_ttm": null,
  "float_shares": null,
  "current": 6.29,  // 当前价
  "amplitude": 502.82,
  "pcf": null,
  "current_year_percent": -86.1,  // 年初至今涨跌百分比
  "float_market_capital": null,
  "north_net_inflow_time": null,
  "market_capital": 2660670,  // 市值
  "dividend_yield": 0,
  "lot_size": 1,
  "roe_ttm": -342.3444749365853,
  "total_percent": null,
  "percent5m": -11.66,
  "income_cagr": 113.74731378730888,
  "amount": 479469734, // 成交额
  "chg": 4.87, // 涨跌额
  "issue_date_ts": 1644163200000, //
  "eps": -37.40664539007092,
  "main_net_inflows": 8501072,
  "volume": 77943943,  // 成交量
  "volume_ratio": 7.41,  // 成交量占比
  "pb": null,
  "followers": 124,
  "turnover_rate": 18426.46,  // 换手率
  "mapping_quote_current": null,
  "first_percent": null,
  "name": "American Rebel",  // 公司名
  "pe_ttm": null,
  "dual_counter_mapping_symbol": null,
  "total_shares": 423000,
  "limitup_days": null
}
'''
