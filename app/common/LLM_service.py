import json
import re
from typing import Dict, Any, List, Optional

from loguru import logger
from common.global_variant import config
from openai import AsyncOpenAI

# === 核心配置区 ===
LLM_CONFIG = {
    "base_url": "https://api.deepseek.com/",
    "api_key": config.LLM.DEEPSEEK_API_KEY,
    "model": "deepseek-v4-flash",
}

# 初始化异步客户端
client = AsyncOpenAI(api_key=LLM_CONFIG["api_key"], base_url=LLM_CONFIG["base_url"])


def _clean_fields(data: Dict[str, Any], expected_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    清洗解析后的字段：过滤多余字段，将字符串中的数值提取为 float/int。
    """
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


def _parse_response(raw: str, expected_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    清洗并解析 LLM 返回的 JSON（处理 Markdown 包裹、字段清洗等）。
    """
    # 尝试直接解析
    try:
        data = json.loads(raw)
        return _clean_fields(data, expected_fields)
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试去除 Markdown 代码块标记后解析
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
        logger.error(f"JSON 解析失败: {text[:200]}")
        return {}

    return _clean_fields(data, expected_fields)


async def call_LLM(content: str, prompt: str, expected_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    调用 DeepSeek 大模型，返回结构化的 JSON 数据。
    """
    if not content or not content.strip():
        return {}

    try:
        response = await client.chat.completions.create(
            model=LLM_CONFIG["model"],
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"请解析以下正文：\n\n{content}"},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        raw_result = response.choices[0].message.content
        return _parse_response(raw_result, expected_fields)

    except Exception as e:
        logger.error(f"DeepSeek API 调用异常: {e}", exc_info=True)
        return {}
