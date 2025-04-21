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


class XueqiuZHHistory(BaseModel):
    """雪球组合指数模型"""

    name = fields.CharField(null=True, max_length=128, description='组合名称')
    symbol = fields.CharField(max_length=16, null=False, db_index=True, description='组合代号')
    history = fields.TextField(description='历史数据')
    class Meta:
        table = 'xueqiu_zh_history'


class XueqiuUser(BaseModel):
    """雪球用户模型"""

    name = fields.CharField(null=True, max_length=128, description="用户名")
    province = fields.CharField(null=True, max_length=32, description="省份")
    city = fields.CharField(null=True, max_length=32, description="城市")
    location = fields.CharField(null=True, max_length=128, description="位置")
    description = fields.TextField(null=True, description="描述")
    url = fields.CharField(null=True, max_length=256, description="个人主页URL")
    domain = fields.CharField(null=True, max_length=64, description="域名")
    gender = fields.CharField(null=True, max_length=1, description="性别")
    verified = fields.BooleanField(null=True, description="是否认证")
    type = fields.CharField(null=True, max_length=8, description="用户类型")
    step = fields.CharField(null=True, max_length=16, description="用户阶段")
    profile = fields.CharField(null=True, max_length=256, description="用户主页路径")
    recommend = fields.CharField(null=True, max_length=256, description="推荐信息")
    intro = fields.TextField(null=True, description="简介")
    status = fields.IntField(null=True, description="状态")
    following = fields.BooleanField(null=True, description="是否关注")
    blocking = fields.BooleanField(null=True, description="是否屏蔽")
    subscribeable = fields.BooleanField(null=True, description="是否可订阅")
    remark = fields.TextField(null=True, description="备注")
    constrained = fields.IntField(null=True, description="限制状态")
    screen_name = fields.CharField(null=True, max_length=128, description="显示名称")
    created_at = fields.BigIntField(null=True, description="创建时间戳")
    followers_count = fields.IntField(null=True, description="粉丝数")
    friends_count = fields.IntField(null=True, description="关注数")
    status_count = fields.IntField(null=True, description="帖子数")
    last_status_id = fields.BigIntField(null=True, description="最后状态ID")
    blog_description = fields.TextField(null=True, description="博客描述")
    st_color = fields.CharField(null=True, max_length=8, description="状态颜色")
    stocks_count = fields.IntField(null=True, description="持股数")
    cube_count = fields.IntField(null=True, description="组合数")
    donate_count = fields.IntField(null=True, description="捐赠数")
    verified_type = fields.IntField(null=True, description="认证类型")
    verified_description = fields.TextField(null=True, description="认证描述")
    verified_realname = fields.BooleanField(null=True, description="是否实名认证")
    stock_status_count = fields.IntField(null=True, description="股票状态数")
    follow_me = fields.BooleanField(null=True, description="是否关注我")
    allow_all_stock = fields.BooleanField(null=True, description="是否允许所有股票")
    name_pinyin = fields.CharField(null=True, max_length=128, description="用户名拼音")
    screenname_pinyin = fields.CharField(null=True, max_length=128, description="显示名称拼音")
    group_ids = fields.JSONField(null=True, description="分组ID")
    common_count = fields.IntField(null=True, description="共同点数量")
    recommend_reason = fields.TextField(null=True, description="推荐理由")
    verified_infos = fields.JSONField(null=True, description="认证信息")
    select_company_background = fields.TextField(null=True, description="公司背景")
    select_company_banners = fields.JSONField(null=True, description="公司横幅")
    privacy_agreement = fields.TextField(null=True, description="隐私协议")
    ip_location = fields.CharField(null=True, max_length=128, description="IP位置")
    reg_time = fields.BigIntField(null=True, description="注册时间")
    national_network_verify = fields.JSONField(null=True, description="国家网络认证")
    photo_domain = fields.CharField(null=True, max_length=256, description="头像域名")
    profile_image_url = fields.TextField(null=True, description="头像URL")

    class Meta:
        table = "xueqiu_user"


class XueqiuRebalancing(BaseModel):
    """雪球组合调仓记录模型"""

    symbol = fields.CharField(max_length=50, null=False, description="组合代号", db_index=True)
    status = fields.CharField(max_length=50, null=True, description="调仓状态", db_index=True)
    cube_id = fields.BigIntField(null=False, description="组合 ID", db_index=True)
    prev_bebalancing_id = fields.BigIntField(null=True, description="上一次调仓 ID")
    category = fields.CharField(max_length=50, null=True, description="调仓分类")
    exe_strategy = fields.CharField(max_length=50, null=True, description="执行策略")
    created_at = fields.BigIntField(null=True, description="创建时间戳")
    updated_at = fields.BigIntField(null=True, description="更新时间戳")
    cash = fields.FloatField(null=True, description="现金比例")
    cash_value = fields.FloatField(null=True, description="现金价值")
    error_code = fields.IntField(null=True, description="错误代码")
    error_message = fields.TextField(null=True, description="错误信息")
    error_status = fields.CharField(max_length=50, null=True, description="错误状态")
    holdings = fields.JSONField(null=True, description="持仓信息")
    rebalancing_histories = fields.JSONField(null=True, description="调仓明细 JSON 数据")
    comment = fields.TextField(null=True, description="用户备注")
    diff = fields.IntField(null=True, description="调仓差异值")
    new_buy_count = fields.IntField(null=True, description="新增买入数量")

    class Meta:
        table = "xueqiu_rebalancing"
'''
{
    "id": 190146035,
    "status": "success",
    "cube_id": 1037635,
    "prev_bebalancing_id": 189952247,
    "category": "sys_rebalancing",
    "exe_strategy": "market_all",
    "created_at": 1743380077719,
    "updated_at": 1743380077719,
    "cash": 96.97,
    "error_code": null,
    "cash_value": 0.01069492,
    "error_message": null,
    "error_status": null,
    "holdings": null,
    "rebalancing_histories": [
        {
            "id": 242448853,
            "rebalancing_id": 190146035,
            "stock_id": 1001695,
            "stock_name": "顺络电子",
            "stock_symbol": "SZ002138",
            "volume": 0.00689206,
            "price": 29.55,
            "net_value": 0.2037,
            "weight": 3.03,
            "target_weight": 3.03,
            "prev_weight": 2.98,
            "prev_target_weight": 2.98,
            "prev_weight_adjusted": 2.97,
            "prev_volume": 0.0067549,
            "prev_price": 29.75,
            "prev_net_value": 0.20095827,
            "proactive": true,
            "created_at": 1743380077719,
            "updated_at": 1743380077719,
            "target_volume": 0.00689206,
            "prev_target_volume": 0.00676081
        }
    ],
    "comment": "",
    "diff": 0,
    "new_buy_count": 0
}
'''
