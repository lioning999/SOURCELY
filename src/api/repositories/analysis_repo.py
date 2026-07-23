"""analysis 表数据访问 — 分析记录 + 子表（spec/sku/price_tier）写入。

覆盖风险清单：
  #12  查询历史存储 → 方案 B（存元数据），存 analysis 表
"""

from typing import Any

import aiomysql  # type: ignore[import-untyped]

from database import AsyncDatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


# ---- INSERT 列名（create / upsert 共用） ----
_INSERT_COLS = (
    "user_id, offer_id, status, title, image_url, "
    "price_min, price_max, moq, unit, "
    "shop_name, shop_years, shop_rate, repurchase, sold, "
    "verdict_product, verdict_factory, verdict_sample, apify_task_id"
)
_INSERT_VALS = "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"


class AnalysisRepository:
    """analysis 表 + 子表 CRUD。事务由 service 层控制。"""

    async def upsert(self, data: dict[str, Any]) -> int:
        """INSERT 或 UPDATE 分析记录 + 子表（ON DUPLICATE KEY UPDATE）。

        已存在 → UPDATE 主表 + DELETE 旧子表 + 重新 INSERT 子表。
        不存在 → INSERT 主表 + INSERT 子表。
        整个操作在一个事务内。
        """
        conn = await AsyncDatabaseConnection.get_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 主表：INSERT ... ON DUPLICATE KEY UPDATE
                await cur.execute(
                    f"""INSERT INTO analysis ({_INSERT_COLS}) VALUES {_INSERT_VALS}
                       ON DUPLICATE KEY UPDATE
                        status=VALUES(status), title=VALUES(title), image_url=VALUES(image_url),
                        price_min=VALUES(price_min), price_max=VALUES(price_max),
                        moq=VALUES(moq), unit=VALUES(unit),
                        shop_name=VALUES(shop_name), shop_years=VALUES(shop_years),
                        shop_rate=VALUES(shop_rate), repurchase=VALUES(repurchase),
                        sold=VALUES(sold),
                        verdict_product=VALUES(verdict_product),
                        verdict_factory=VALUES(verdict_factory),
                        verdict_sample=VALUES(verdict_sample),
                        updated_at=NOW()""",
                    (
                        data["user_id"], data["offer_id"], data.get("status", "done"),
                        data.get("title"), data.get("image_url"),
                        data.get("price_min"), data.get("price_max"),
                        data.get("moq"), data.get("unit"),
                        data.get("shop_name"), data.get("shop_years"), data.get("shop_rate"),
                        data.get("repurchase"), data.get("sold"),
                        data.get("verdict_product"), data.get("verdict_factory"),
                        data.get("verdict_sample"), data.get("apify_task_id"),
                    ),
                )
                analysis_id = cur.lastrowid

                # 子表：先删再插（幂等）
                for table in ("analysis_spec", "analysis_sku", "analysis_price_tier"):
                    await cur.execute(f"DELETE FROM {table} WHERE analysis_id=%s", (analysis_id,))

                specs: list[dict[str, Any]] = data.get("specs", []) or []
                for s in specs:
                    await cur.execute(
                        "INSERT INTO analysis_spec (analysis_id, spec_key, spec_value) VALUES (%s,%s,%s)",
                        (analysis_id, s.get("spec_key"), s.get("spec_value")),
                    )

                skus: list[dict[str, Any]] = data.get("skus", []) or []
                for sku in skus:
                    await cur.execute(
                        "INSERT INTO analysis_sku (analysis_id, sku_name, sku_image) VALUES (%s,%s,%s)",
                        (analysis_id, sku.get("sku_name"), sku.get("sku_image")),
                    )

                tiers: list[dict[str, Any]] = data.get("price_tiers", []) or []
                for t in tiers:
                    await cur.execute(
                        "INSERT INTO analysis_price_tier (analysis_id, qty_min, qty_max, unit_price) VALUES (%s,%s,%s,%s)",
                        (analysis_id, t.get("qty_min"), t.get("qty_max"), t.get("unit_price")),
                    )

                await conn.commit()
                return analysis_id  # type: ignore[return-value]
        except Exception:
            await conn.rollback()
            raise
        finally:
            await AsyncDatabaseConnection.close_connection(conn)

    async def get_history(self, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        """查用户最近的分析记录。"""
        conn = await AsyncDatabaseConnection.get_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT id, offer_id, title, image_url, price_min, price_max, moq, unit,
                              shop_name, verdict_product, created_at
                       FROM analysis
                       WHERE user_id=%s AND status='done'
                       ORDER BY created_at DESC LIMIT %s""",
                    (user_id, limit),
                )
                return await cur.fetchall()  # type: ignore[return-value]
        finally:
            await AsyncDatabaseConnection.close_connection(conn)
