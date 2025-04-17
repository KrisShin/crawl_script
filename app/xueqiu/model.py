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
    national_network_verify = fields.TextField(null=True, description="国家网络认证")
    photo_domain = fields.CharField(null=True, max_length=256, description="头像域名")
    profile_image_url = fields.TextField(null=True, description="头像URL")

    class Meta:
        table = "xueqiu_user"

'''
{
    "id": 9522147036,
    "name": null,
    "province": "贵州",
    "city": "遵义",
    "location": null,
    "description": "",
    "url": null,
    "domain": null,
    "gender": "m",
    "verified": false,
    "type": "1",
    "step": "three",
    "profile": "/9522147036",
    "recommend": null,
    "intro": null,
    "status": 1,
    "following": false,
    "blocking": false,
    "subscribeable": false,
    "remark": null,
    "constrained": 0,
    "screen_name": "ZZ贵州茅台价值之道",
    "created_at": 1355461673627,
    "followers_count": 9842,
    "friends_count": 62,
    "status_count": 367,
    "last_status_id": 331916355,
    "blog_description": null,
    "st_color": "1",
    "stocks_count": 14,
    "cube_count": 1,
    "donate_count": 0,
    "verified_type": 0,
    "verified_description": null,
    "verified_realname": false,
    "stock_status_count": null,
    "follow_me": false,
    "allow_all_stock": false,
    "name_pinyin": null,
    "screenname_pinyin": null,
    "group_ids": null,
    "common_count": 0,
    "recommend_reason": null,
    "verified_infos": [],
    "select_company_background": null,
    "select_company_banners": null,
    "privacy_agreement": null,
    "ip_location": "贵州",
    "reg_time": 0,
    "national_network_verify": null,
    "photo_domain": "//xavatar.imedao.com/",
    "profile_image_url": "community/20131/1360865157600-1360865175892.png,community/20131/1360865157600-1360865175892.png!180x180.png,community/20131/1360865157600-1360865175892.png!50x50.png,community/20131/1360865157600-1360865175892.png!30x30.png"
}
'''
