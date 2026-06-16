import json
import re
import time
from typing import Any, Dict, List, Optional

from loguru import logger
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models


class LLMClient:
    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        model: str = "hunyuan-lite",
        region: str = "ap-guangzhou",
        timeout: int = 1000,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ):
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._model = model
        self._region = region
        self._timeout = timeout
        self._max_retries = max_retries
        self._base_delay = base_delay

    def _build_client(self) -> hunyuan_client.HunyuanClient:
        cred = credential.Credential(self._secret_id, self._secret_key)
        cpf = ClientProfile()
        cpf.httpProfile.pre_conn_pool_size = 3
        cpf.httpProfile.reqTimeout = self._timeout
        return hunyuan_client.HunyuanClient(cred, self._region, cpf)

    def call(self, content: str, prompt: str, expected_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        last_exception = None
        for attempt in range(self._max_retries):
            try:
                client = self._build_client()
                req = models.ChatCompletionsRequest()
                req.Model = self._model

                sys_msg = models.Message()
                sys_msg.Role = "system"
                sys_msg.Content = prompt

                user_msg = models.Message()
                user_msg.Role = "user"
                user_msg.Content = content

                req.Messages = [sys_msg, user_msg]
                req.Stream = False

                resp = client.ChatCompletions(req)
                full_content = (
                    resp.Choices[0].Message.Content
                    .replace('：', ': ')
                    .replace('\n', '')
                )
                return self._parse_response(full_content, expected_fields)

            except TencentCloudSDKException as err:
                logger.error(f"Hunyuan SDK error (attempt {attempt + 1}/{self._max_retries}): {err}")
                last_exception = err
            except Exception as err:
                logger.error(f"Hunyuan call error (attempt {attempt + 1}/{self._max_retries}): {err}", exc_info=True)
                last_exception = err

            if attempt < self._max_retries - 1:
                delay = self._base_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)

        logger.error(f"All {self._max_retries} attempts failed. Last error: {last_exception}")
        return {}

    @staticmethod
    def _parse_response(raw: str, expected_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            data = json.loads(raw)
            return LLMClient._clean_fields(data, expected_fields)
        except (json.JSONDecodeError, TypeError):
            pass

        text = raw.strip()
        pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end + 1]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"JSON parse failed: {text[:200]}")
            return {}

        return LLMClient._clean_fields(data, expected_fields)

    @staticmethod
    def _clean_fields(data: Dict[str, Any], expected_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        cleaned: Dict[str, Any] = {}
        for key, value in data.items():
            if expected_fields and key not in expected_fields:
                continue

            if value is None:
                cleaned[key] = None
                continue
            if isinstance(value, (int, float)):
                cleaned[key] = value
                continue
            if isinstance(value, str):
                num_match = re.search(r"(-?\d+(?:\.\d+)?)", value)
                if num_match:
                    try:
                        num_val = float(num_match.group(1))
                        cleaned[key] = int(num_val) if key in ('year', 'month') else num_val
                    except (ValueError, TypeError):
                        cleaned[key] = None
                else:
                    cleaned[key] = None
        return cleaned
