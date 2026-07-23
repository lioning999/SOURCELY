"""Apify 1688 Wholesale Scraper 适配器 — 封装 ApifyClientAsync SDK。

覆盖风险清单：
  #3  90s 超时 → wait_duration=timedelta(seconds=Config.APIFY_WAIT_SECONDS)
"""

from typing import Any
from datetime import timedelta

from apify_client import ApifyClientAsync
from apify_client.errors import ApifyApiError

from config import Config
from domain.urls import extract_offer_id
from utils.exceptions import ExternalServiceError
from utils.logger import get_logger

logger = get_logger(__name__)


class ApifyAdapter:
    """Apify 1688 Wholesale Scraper 适配器。

    使用官方 ApifyClientAsync SDK：
    actor.call(run_input, wait_duration) → 启动 run + 等待完成 → 取 dataset items。

    ApifyClientAsync v3.x 不支持 async with，直接实例化使用。
    内部 httpx 客户端随对象生命周期管理。
    """

    def __init__(self, token: str = ""):
        self.token = token or Config.APIFY_TOKEN

    def __init__(self, token: str = ""):
        self.token = token or Config.APIFY_TOKEN  # 默认 token，向后兼容
        self.tokens = Config.APIFY_TOKENS          # 多 token 列表

    async def fetch_product_by_url(self, url: str) -> dict[str, Any] | None:
        """根据 1688 商品链接获取结构化数据。

        多 token 自动切换：一个 token 配额耗尽 → 自动尝试下一个。

        Args:
            url: 1688 商品详情页完整 URL

        Returns:
            商品数据 dict（dataset 第一条），超时或失败返回 None

        Raises:
            ExternalServiceError: 所有 token 都不可用时
        """
        offer_id = extract_offer_id(url)
        if not offer_id:
            logger.warning(f"无法从 URL 提取 offerId: {url[:80]}")
            return None

        last_error: Exception | None = None
        tokens = self.tokens if self.tokens else [self.token]

        for i, token in enumerate(tokens):
            if not token:
                continue
            client = ApifyClientAsync(token=token)

            try:
                run = await client.actor(Config.APIFY_ACTOR_ID).call(
                    run_input={"offerIds": [offer_id]},
                    wait_duration=timedelta(seconds=Config.APIFY_WAIT_SECONDS),
                )

                if run is None:
                    logger.warning(f"Apify run returned None: offer_id={offer_id}")
                    continue

                page = await client.dataset(run.default_dataset_id).list_items(limit=1)
                items: list[dict[str, Any]] = page.items
                if not items:
                    logger.warning(f"Apify dataset 为空: offer_id={offer_id}")
                    return None

                # 检测配额耗尽：Apify 免费额度用完后返回 limit_reached 标记
                if len(items) == 1 and items[0].get("limit_reached"):
                    logger.warning(f"Apify token {i+1}/{len(tokens)} 配额耗尽，切换下一个")
                    continue

                logger.info(f"Apify fetch done: offer_id={offer_id}  token_index={i+1}")
                return items[0]

            except ApifyApiError as e:
                logger.error(f"Apify API 异常 (token {i+1}): offer_id={offer_id} error={e}")
                last_error = e
                continue

        if last_error:
            raise ExternalServiceError(service_name="Apify", details={"offer_id": offer_id}) from last_error
        logger.error(f"所有 Apify token 配额已耗尽: offer_id={offer_id}")
        return None


# 模块级单例
apify_adapter = ApifyAdapter()
