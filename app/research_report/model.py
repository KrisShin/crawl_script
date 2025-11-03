# models.py
from tortoise import models, fields


class ResearchReport(models.Model):
    """
    研究报告数据模型
    对应数据库中的 research_report 表
    """

    id = fields.BigIntField(pk=True)
    site = fields.CharField(max_length=100, description='来自站点')
    title = fields.CharField(max_length=500, description='报告标题')
    article_url = fields.CharField(max_length=500, unique=True, description='原文网页链接')
    file_url = fields.JSONField(description='原文下载链接 (JSON 格式)')  # 可能有多个文件, 所以用json
    download_url = fields.CharField(max_length=500, null=True, description='对外下载链接')

    # 对应你的 `pulish_date` 字段
    pulish_date = fields.CharField(max_length=10, null=True, description='发布日期')

    class Meta:
        table = "research_report"

    def __str__(self):
        return self.title
