"""Apify 1688 Wholesale Scraper 适配器 — 封装 Apify REST API 调用。"""

import asyncio
import httpx
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class ApifyAdapter:
    """Apify 1688 Wholesale Scraper 适配器。

    封装 Zen Studio actor 的完整调用流程：
    启动 run → 轮询 dataset → 返回商品数据。
    """

    BASE_URL = "https://api.apify.com/v2"
    ACTOR_PATH = f"acts/{Config.APIFY_ACTOR_ID}/runs"

    def __init__(self, token: str = "", timeout: int | None = None, poll_interval: int | None = None):
        self.token = token or Config.APIFY_TOKEN
        self.timeout = timeout if timeout is not None else Config.APIFY_TIMEOUT
        self.poll_interval = poll_interval if poll_interval is not None else Config.APIFY_POLL_INTERVAL
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    async def fetch_product_by_url(self, url: str) -> dict | None:
        """根据 1688 商品链接获取结构化数据。

        Args:
            url: 1688 商品详情页完整 URL，如 https://detail.1688.com/offer/123456.html

        Returns:
            商品数据 dict，超时或失败返回 None
        """
        # 1. 启动 Apify run
        run_id, dataset_id = await self._start_run(url)
        if not run_id:
            return None

        # 2. 轮询 dataset 直到拿到数据或超时
        return await self._poll_dataset(dataset_id)

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    async def _start_run(self, url: str) -> tuple[str | None, str | None]:
        """启动 Apify Actor run，返回 (run_id, dataset_id)。"""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{self.BASE_URL}/{self.ACTOR_PATH}",
                    json={"offerIds": [_extract_offer_id(url)]},
                    headers=self._headers,
                )
                resp.raise_for_status()
                data = resp.json()
                run_id = data["data"]["id"]
                dataset_id = data["data"]["defaultDatasetId"]
                logger.info(f"Apify run started: {run_id}")
                return run_id, dataset_id
            except httpx.HTTPError as e:
                logger.error(f"Apify start run failed: {e}")
                return None, None

    async def _poll_dataset(self, dataset_id: str) -> dict | None:
        """轮询 dataset，每次间隔 poll_interval 秒，最多 timeout 秒。"""
        dataset_url = f"{self.BASE_URL}/datasets/{dataset_id}/items"
        async with httpx.AsyncClient(timeout=15) as client:
            for _ in range(self.timeout // self.poll_interval):
                await asyncio.sleep(self.poll_interval)
                try:
                    resp = await client.get(dataset_url, headers=self._headers)
                    resp.raise_for_status()
                    items = resp.json()
                    if items:
                        logger.info(f"Apify dataset ready, {len(items)} items")
                        return items[0]
                except httpx.HTTPError as e:
                    logger.warning(f"Apify poll failed: {e}")
                    continue
        logger.warning(f"Apify dataset timeout after {self.timeout}s")
        return None


def _extract_offer_id(url: str) -> str:
    """从 1688 URL 提取 offerId，如 'https://detail.1688.com/offer/997934724655.html' → '997934724655'。"""
    import re
    m = re.search(r"offer/(\d+)", url)
    return m.group(1) if m else url


# 模块级单例
apify_adapter = ApifyAdapter()
