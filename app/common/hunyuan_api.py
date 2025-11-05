# -*- coding: utf-8 -*-
import json
from common.global_variant import config

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models


def call_hunyuan(content: str, prompt: str):
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
        msg = models.Message()
        msg.Role = "user"
        msg.Content = f"""{prompt}{content}"""
        req.Messages = [msg]

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
            from traceback import print_exc

            print_exc()
            print(full_content)
            return False, False, False

    except TencentCloudSDKException as err:
        print(err)
    except Exception as err:
        from traceback import print_exc

        print_exc()
        print(err)


if __name__ == '__main__':
    call_hunyuan('你好', 'test')
