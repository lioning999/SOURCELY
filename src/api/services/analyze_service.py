"""1688 商品分析服务 — 业务编排 + Apify 数据 → 前端字段映射。"""

from adapters.apify_adapter import apify_adapter
from utils.exceptions import ExternalServiceError


class AnalyzeService:
    """1688 商品分析服务。

    映射 Zen Studio 1688 Wholesale Scraper 返回的实际字段 → 前端展示字段。
    """

    CNY_TO_USD = 7.2  # 人民币→美元 粗略汇率

    async def analyze(self, url: str) -> dict:
        raw = await apify_adapter.fetch_product_by_url(url)
        if raw is None:
            raise ExternalServiceError(service_name="Apify 1688 数据抓取")
        return self._map(raw, url)

    # ------------------------------------------------------------------
    # 映射
    # ------------------------------------------------------------------

    def _map(self, raw: dict, original_url: str) -> dict:
        price_data = raw.get("price") or {}
        supplier = raw.get("supplier") or {}
        flags = supplier.get("flags", {}) or {}
        shipping = raw.get("shipping") or {}

        price_low_cny = price_data.get("min") or 0
        price_high_cny = price_data.get("max") or price_low_cny

        # 发货地 + 产业带
        location = shipping.get("location", "")
        cluster = self._industry_cluster(location)

        return {
            # ---- 产品信息 ----
            "title": raw.get("title", ""),
            "image": (raw.get("images") or [""])[0] if raw.get("images") else "",
            "images": (raw.get("images") or [])[:5],
            "descriptionImages": (raw.get("descriptionImages") or [])[:10],
            "priceLow": self._cny_to_usd(price_low_cny),
            "priceHigh": self._cny_to_usd(price_high_cny),
            "priceCNY": {"low": price_low_cny, "high": price_high_cny},
            "moq": raw.get("minOrderQuantity"),
            "itemUrl": original_url or raw.get("detailUrl", ""),
            "specs": self._filter_specs(raw.get("specs", []) or []),
            "stock": raw.get("stock"),
            "isOutOfStock": raw.get("isOutOfStock", False),
            "unit": raw.get("unit", ""),

            # ---- 产品指标 ----
            "return7day": "OK" if self._has_tag(raw.get("serviceLabels", []) or [], "7天") or self._has_tag(raw.get("serviceLabels", []) or [], "退货") else "NO",
            "sales30d": str(raw.get("saledCount", "")) if raw.get("saledCount") else "N/A",
            "sales30dAmount": self._calc_sales_amount(raw),
            "wantBuyCount": raw.get("wantBuyCount", 0),
            "serviceTags": self._translate_services(raw.get("services", []) or []),

            # ---- 工厂信息 ----
            "supplierName": supplier.get("companyName", ""),
            "verified": "OK" if self._is_verified(flags) else "NO",
            "verifiedTags": self._flag_labels(flags),
            "businessType": self._business_type(flags),
            "shippingLocation": location,
            "industryCluster": cluster,
            "shippingSpeed": "OK" if shipping.get("deliveryDays", 99) <= 2 else "NO",
            "shippingSpeedLabel": shipping.get("logisticsText", "N/A"),
        }

    # ------------------------------------------------------------------
    # 提取工具
    # ------------------------------------------------------------------

    @staticmethod
    def _has_tag(tags: list, keyword: str) -> bool:
        return any(keyword in str(t) for t in tags)

    @staticmethod
    def _is_verified(flags: dict) -> bool:
        """任一认证标识为真即算已认证。"""
        checks = ["isFactoryDealer", "isSuperFactory", "isTpFactory",
                   "isChtMember", "isSiliCertifiedBrand", "isFactory"]
        return any(flags.get(k) for k in checks)

    @staticmethod
    def _flag_labels(flags: dict) -> list:
        """供应商认证标签 → 中文/英文列表。"""
        MAP = {
            "isChtMember": "诚信通",
            "isSuperFactory": "超级工厂",
            "isTpFactory": "TP验厂",
            "isFactoryDealer": "厂货通",
            "isShiliFactory": "实力工厂",
            "isSiliCertifiedBrand": "品牌认证",
            "isFactory": "生产厂家",
            "isTp": "第三方认证",
        }
        return [label for key, label in MAP.items() if flags.get(key)]

    @staticmethod
    def _business_type(flags: dict) -> str:
        if flags.get("isFactory"):
            return "生产厂家"
        if flags.get("isFactoryDealer"):
            return "厂货通商家"
        return "经销商（推测）"

    @staticmethod
    def _calc_sales_amount(raw: dict) -> str:
        count = raw.get("saledCount")
        price = (raw.get("price") or {}).get("min")
        if count and price:
            try:
                return f"¥{int(count) * float(price):,.0f}"
            except (ValueError, TypeError):
                pass
        return "N/A"

    @staticmethod
    def _cny_to_usd(cny) -> float | None:
        if cny is None:
            return None
        try:
            return round(float(cny) / AnalyzeService.CNY_TO_USD, 2)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _filter_specs(specs: list) -> list[dict]:
        """过滤关键规格：材质、品牌、颜色、规格、尺寸、风格。最多 5 个。"""
        KEYS = {"材质", "品牌", "颜色", "规格", "尺寸", "风格", "货号", "重量", "包装"}
        result: list[dict] = []
        for s in specs:
            name = str(s.get("name", "")).strip()
            value = str(s.get("value", "")).strip()
            if name in KEYS and value and value != "咨询客服" and len(value) < 30:
                result.append({"name": name, "value": value})
        # 材质优先
        result.sort(key=lambda x: 0 if x["name"] == "材质" else 1)
        return result[:5]

    @staticmethod
    def _translate_services(services: list) -> list[dict]:
        """翻译 1688 服务标签 → {name, desc}（人话解释）。"""
        MAP: dict[str, str] = {
            "晚发必赔": "晚发货可申请赔付",
            "48小时发货": "下单后 48h 内发出",
            "24小时发货": "下单后 24h 内发出",
            "品质保障": "质量有问题可协商补偿",
            "破损补寄": "收到破损免费补发",
            "7天无理由": "7 天内可无理由退货",
            "包邮": "国内段免运费（部分偏远地区除外）",
            "混批": "满一定金额或数量可混批采购",
            "一件代发": "支持一件代发，无需囤货",
            "闪电发货": "当天或次日极速发出",
            "实力商家": "通过 1688 实力商家认证",
            "品牌授权": "品牌方授权经销",
            "免费拿样": "可免费申请样品",
        }
        result: list[dict] = []
        seen: set[str] = set()
        for sv in services:
            name = str(sv.get("name", "")).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            desc = MAP.get(name, sv.get("description", name))
            result.append({"name": name, "desc": desc})
        return result[:4]

    @staticmethod
    def _industry_cluster(location: str) -> str:
        """根据发货地匹配中国产业带（静态映射表）。"""
        if not location:
            return ""
        MAP: dict[str, str] = {
            "兴城": "中国泳装产业带 — 占全国泳装产量 70%",
            "曹县": "中国汉服/演出服产业带",
            "织里": "中国童装产业带",
            "义乌": "中国小商品集散中心",
            "广州": "服装/箱包/皮具产业带",
            "深圳": "3C 电子/跨境电商货源地",
            "晋江": "运动鞋服产业带",
            "南通": "家纺产业带",
            "泉州": "鞋服箱包产业带",
            "潮州": "陶瓷/卫浴产业带",
            "东莞": "电子/玩具/模具产业带",
            "佛山": "家具/陶瓷产业带",
            "白沟": "箱包产业带",
            "濮院": "毛衫产业带",
            "虎门": "女装产业带",
            "杭州": "女装/电商供应链中心",
            "温州": "鞋革/五金/眼镜产业带",
            "宁波": "小家电/文具产业带",
            "绍兴": "纺织面料产业带",
            "许昌": "假发产业带",
            "澄海": "玩具产业带",
            "景德镇": "陶瓷产业带",
            "连云港": "水晶/珠宝产业带",
            "诸暨": "袜子/珍珠产业带",
            "永康": "五金/杯壶产业带",
        }
        for key, desc in MAP.items():
            if key in location:
                return desc
        return ""


# 单例
analyze_service = AnalyzeService()
