""" JSON解析工具模块 """

import json
import re
import logging

logger = logging.getLogger(__name__)

_MD_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)


def _strip_markdown_fences(text: str) -> str:
    """去除 markdown 代码块包裹（```json ... ```）"""
    m = _MD_FENCE_RE.match(text)
    return m.group(1).strip() if m else text


def safe_parse_json(data, fallback=None):
    """
    安全解析JSON字符串

    参数:
        data: 要解析的JSON字符串或数据
        fallback: 解析失败时的默认返回值

    返回:
        解析后的JSON对象或fallback值
    """
    if data is None:
        return fallback

    if isinstance(data, (dict, list)):
        return data

    if not isinstance(data, str):
        return fallback

    cleaned = _strip_markdown_fences(data)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失败: {e}, 数据: {data[:100]}")
        return fallback
    except Exception as e:
        logger.error(f"JSON解析异常: {e}")
        return fallback