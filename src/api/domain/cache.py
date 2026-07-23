"""offer_id 内存缓存 — TTL 30min, LRU 淘汰, 500 条上限。

覆盖风险清单：
  #1  同链接重复调用 → 缓存命中直接返回
  #14 L2 防刷缓存层 → 30min TTL 防高频刷同一商品
"""

import time
from typing import Any

# {offer_id: (timestamp, data)}
cache: dict[str, tuple[float, dict[str, Any]]] = {}
MAX_SIZE = 500
TTL = 1800  # 30 分钟


def get(offer_id: str) -> dict[str, Any] | None:
    """查缓存。命中且未过期返回数据，过期自动清理。"""
    entry = cache.get(offer_id)
    if entry is None:
        return None
    ts, data = entry
    if time.time() - ts < TTL:
        return data
    # 过期清理
    del cache[offer_id]
    return None


def set(offer_id: str, data: dict[str, Any]) -> None:
    """写缓存。超上限时 LRU 淘汰最老条目。"""
    if len(cache) >= MAX_SIZE and offer_id not in cache:
        oldest = min(cache, key=lambda k: cache[k][0])
        del cache[oldest]
    cache[offer_id] = (time.time(), data)


