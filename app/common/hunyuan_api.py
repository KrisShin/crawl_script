# -*- coding: utf-8 -*-
import json
import re

from loguru import logger
from common.global_variant import config

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models


def _clean_and_parse_json(response_text: str, expected_fields) -> dict:
    """
    清洗并解析 LLM 返回的 JSON
    1. 去除 Markdown
    2. 递归将所有 value 中的单位去除并转为 float/int
    """
    # 1. 提取 JSON 字符串
    text = response_text.strip()
    # 移除 ```json 包裹
    pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        # 尝试暴力截取 {}
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start : end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"JSON 解析彻底失败: {text}")
        return {}

    # 2. 字段类型清洗 (去除 '万', '亿', '%' 等)
    cleaned_data = {}

    for key, value in data.items():
        # 过滤掉不在白名单里的字段 (解决 Case 1 多余字段问题)
        if expected_fields and key not in expected_fields:
            continue

        if value is None:
            cleaned_data[key] = None
            continue

        # 如果是数字，直接保留
        if isinstance(value, (int, float)):
            cleaned_data[key] = value
            continue

        # 如果是字符串，尝试清洗 (解决 Case 3 单位问题)
        if isinstance(value, str):
            # 提取字符串中的第一个浮点数
            # 匹配规则: 可选负号 + 数字 + 可选小数点 + 数字
            num_match = re.search(r"(-?\d+(?:\.\d+)?)", value)
            if num_match:
                try:
                    num_val = float(num_match.group(1))
                    # 如果是年份或月份，转int
                    if key in ['year', 'month']:
                        cleaned_data[key] = int(num_val)
                    else:
                        cleaned_data[key] = num_val
                except:
                    cleaned_data[key] = None
            else:
                cleaned_data[key] = None

    return cleaned_data


def call_hunyuan(content: str, prompt: str, expected_fields: list = None):
    """调用腾讯混元模型"""

    try:
        # 实例化一个认证对象，入参需要传入腾讯云账户secretId，secretKey
        cred = credential.Credential(config.hunyuan.TENCENTCLOUD_SECRET_ID, config.hunyuan.TENCENTCLOUD_SECRET_KEY)

        cpf = ClientProfile()
        # 预先建立连接可以降低访问延迟
        cpf.httpProfile.pre_conn_pool_size = 3
        cpf.httpProfile.reqTimeout = 1000  # 流式接口可能耗时较长
        client = hunyuan_client.HunyuanClient(cred, "ap-guangzhou", cpf)

        req = models.ChatCompletionsRequest()
        req.Model = "hunyuan-lite"
        sys_msg = models.Message()
        sys_msg.Role = "system"
        sys_msg.Content = prompt
        msg = models.Message()
        msg.Role = "user"
        msg.Content = content
        req.Messages = [sys_msg, msg]

        # hunyuan ChatCompletions 同时支持 stream 和非 stream 的情况
        req.Stream = False
        resp = client.ChatCompletions(req)

        full_content = ""
        if req.Stream:  # stream 示例
            for event in resp:
                print(event["data"])
                data = json.loads(event['data'])
                for choice in data['Choices']:
                    full_content += choice['Delta']['Content']
        else:  # 非 stream 示例
            # 通过 Stream=False 参数来指定非 stream 协议, 一次性拿到结果
            full_content = resp.Choices[0].Message.Content.replace('：', ': ').replace('\n', '')
        try:
            resp_json = json.loads(full_content)
            return resp_json
        except:
            res = _clean_and_parse_json(full_content, expected_fields)
            if res:
                return res
            from traceback import print_exc

            print_exc()
            return False, False, False

    except TencentCloudSDKException as err:
        print(err)
    except Exception as err:
        from traceback import print_exc

        print_exc()
        print(err)


if __name__ == '__main__':
    call_hunyuan('你好', 'test')
