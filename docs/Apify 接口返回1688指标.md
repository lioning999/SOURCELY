 Apify 1688 Wholesale Scraper 完整调用方案
一、Python 调用方式（最简）

from apify_client import ApifyClient

client = ApifyClient("your-apify-token")

# 方式1：按商品ID（最常用）
run = client.actor("zen-studio/1688-wholesale-scraper").call(
    run_input={"offerIds": ["997934724655", "1234567890"]}
)

# 方式2：按商品链接
run = client.actor("zen-studio/1688-wholesale-scraper").call(
    run_input={"offerUrls": ["https://detail.1688.com/offer/997934724655.html"]}
)

# 方式3：按店铺首页
run = client.actor("zen-studio/1688-wholesale-scraper").call(
    run_input={"shopUrls": ["https://shop.1688.com/xxxx"]}
)

# 方式4：按搜索关键词
run = client.actor("zen-studio/1688-wholesale-scraper").call(
    run_input={"keyword": "蓝牙耳机"}
)

# 取结果
items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
product = items[0]  # 第一个商品
安装： pip install apify-client

### 为什么用 apify-client 而非 httpx 直调？

| | httpx 直调 | apify-client |
|---|---|---|
| 代码量 | ~100 行 | ~30 行 |
| 轮询逻辑 | 手写 while+sleep | SDK 内置 wait_for_finish |
| 超时重试 | 自己实现 | SDK 内置指数退避 |
| Apify API 变更 | 手动跟进 | SDK 自动适配 |
| 依赖 | httpx（项目已有） | pip install apify-client |
| 官方支持 | 无 | Apify 官方维护 |

**结论：用 apify-client。** 多一个依赖但代码量减半，轮询/重试/超时都是内置的，官方维护更稳。

### Sourcely 实际调用代码

```python
import asyncio
from apify_client import ApifyClient
from config import Config

class ApifyAdapter:
    def __init__(self):
        self.client = ApifyClient(Config.APIFY_TOKEN)

    async def fetch_product_by_url(self, url: str) -> dict | None:
        offer_id = _extract_offer_id(url)
        run = await asyncio.to_thread(
            self.client.actor(Config.APIFY_ACTOR_ID).call,
            run_input={"offerIds": [offer_id]}
        )
        items = list(
            self.client.dataset(run["defaultDatasetId"]).iterate_items()
        )
        return items[0] if items else None


def _extract_offer_id(url: str) -> str:
    import re
    m = re.search(r"offer/(\d+)", url)
    return m.group(1) if m else url
```

> `async` 通过 `asyncio.to_thread` 包装，因为 `apify-client` 是同步库。Actor 启动 + 轮询约 5-40s，不阻塞事件循环。

---

二、全部返回字段清单
2.1 产品基本信息
字段	解释	星级	备注
offerId	1688 商品唯一ID	⭐⭐⭐	标识用
title	产品标题	⭐⭐⭐	确认产品
detailUrl	商品页链接	⭐⭐	跳转1688原页面
images	产品图片列表(全量)	⭐⭐⭐	详情/首图素材
videoUrl	产品视频链接	⭐⭐	极少有
skuImages	SKU规格图片	⭐⭐	颜色/尺寸变体图
unit	单位(件/个/套/KG)	⭐⭐	价格展示辅助
categoryName	类目名称	⭐⭐	产品分类
categoryPath	类目全路径	⭐⭐	定位细分市场
scrapedAt	抓取时间戳	⭐	数据时效
2.2 价格
字段	解释	星级	备注
price.min	最低价(CNY)	⭐⭐⭐⭐⭐	核心
price.max	最高价(CNY)	⭐⭐⭐⭐	价格区间
price.currency	货币(CNY)	⭐	固定CNY
price.priceType	价格类型	⭐⭐	批发价/零售价
quantityPrices[]	阶梯批发价	⭐⭐⭐⭐	每档的quantityRange/price
2.3 产品规格
字段	解释	星级	备注
specs[].name	规格名(材质/品牌/颜色等)	⭐⭐⭐⭐	15-20个属性
specs[].value	规格值	⭐⭐⭐⭐	验证产品匹配度
skuDetails.priceRange	SKU价格区间	⭐⭐⭐	选色选码定价
skuDetails.properties[]	规格维度(颜色/尺寸)	⭐⭐⭐	
skuDetails.variants[]	逐SKU价格/库存/图片	⭐⭐⭐	includeSkuDetails=true才返回
unitWeight	单件重量(kg)	⭐⭐⭐⭐	运费估算
customization.supported	是否支持定制/OEM	⭐⭐⭐⭐	贴牌机会
2.4 销量与热度
字段	解释	星级	备注
saledCount	累计销量(数字)	⭐⭐⭐⭐⭐	核心热度指标
saledCountStr	销量展示(如"5万+")	⭐⭐⭐	
orderCount	30天订单数	⭐⭐⭐⭐	近期热度
recentSoldCount	近期销量	⭐⭐⭐	
soldDisplay	平台展示销量(如"全网10万+件")	⭐⭐⭐	
wantBuyCount	想买人数	⭐⭐⭐	社会化证明
stock	库存量	⭐⭐⭐	
isOutOfStock	是否断货	⭐⭐⭐	预警
supportsSampling	是否支持拿样	⭐⭐⭐⭐	直接对应"拿样"Tab
minOrderQuantity	最小起批量	⭐⭐⭐⭐⭐	核心决策依据
2.5 复购/回头率
字段	解释	星级	备注
returnRate	回头率	⭐⭐⭐⭐	品质佐证(非退货率)
repurchaseRate	复购率(同returnRate)	⭐⭐⭐⭐	同上
offerRepurchaseRate	单品复购率	⭐⭐⭐⭐	比店铺复购更精准
2.6 产品标签/服务
字段	解释	星级	备注
services[].name	售后服务名	⭐⭐⭐	品质保障/48h发货/7天无理由等
services[].description	服务说明	⭐⭐⭐	人话解释
serviceLabels[]	服务标签简写	⭐⭐	数组
serviceTags[]	服务标签	⭐⭐	同上
tags[]	商品标签	⭐⭐	
promotionTags[]	促销标签	⭐⭐	
productFlags.isFreeSample	是否支持免费拿样	⭐⭐⭐⭐	
productFlags.isCrossBorder	是否跨境专供	⭐⭐⭐⭐	印尼卖家关心的
productFlags.isOnePiece	是否支持一件	⭐⭐⭐	代发友好
productFlags.isWholesale	是否批发	⭐⭐	
productFlags.supportsCustomization	是否支持定制	⭐⭐⭐	
promotions[]	店铺促销活动	⭐⭐	
coupons[]	商品优惠券	⭐⭐	
2.7 供应商基本信息
字段	解释	星级	备注
supplier.companyName	公司名	⭐⭐⭐⭐⭐	核心，交叉验证
supplier.legalCompanyName	工商注册全名	⭐⭐⭐⭐⭐	天眼查/企查查关键词
supplier.memberId	会员ID	⭐	
supplier.userId	用户ID	⭐	
supplier.loginId	登录名	⭐	
supplier.foundedYear	成立年份	⭐⭐⭐⭐	经营年限判断
supplier.province / city	省/市	⭐⭐⭐	
supplier.address	完整地址	⭐⭐⭐	
supplier.coordinates	经纬度	⭐	地图展示用
supplier.mainCategory	主营类目	⭐⭐⭐	
supplier.shopUrl	店铺首页链接	⭐⭐⭐	二次抓取
2.8 经营模式与资质（⭐⭐⭐⭐⭐ 核心背调）
字段	解释	星级	备注
supplier.bizType	经营类型(如"生产加工"/"经销批发")	⭐⭐⭐⭐⭐	核心判定依据
supplier.sellerType	商家类型(super_factory/verifiedMerchant)	⭐⭐⭐⭐⭐	
supplier.flags.isFactory	是否是生产厂家	⭐⭐⭐⭐⭐	最关键flag
supplier.flags.isSuperFactory	是否是超级工厂	⭐⭐⭐⭐⭐	1688头部认证
supplier.flags.isTpFactory	是否是TP验厂	⭐⭐⭐⭐	第三方实地验厂
supplier.flags.isShiliFactory	是否是实力工厂	⭐⭐⭐⭐	
supplier.flags.isSiliCertifiedBrand	是否是品牌认证	⭐⭐⭐⭐	
supplier.flags.isChtMember	是否是诚信通会员	⭐⭐⭐	基础认证
supplier.flags.isFactoryDealer	是否是厂货通	⭐⭐⭐⭐	
supplier.flags.isYuantouFlagship	是否是源头旗舰	⭐⭐⭐⭐⭐	源头厂家
supplier.flags.isIndustrySeller	是否是行业商家	⭐⭐⭐	
supplier.flags.isHyper	是否是实力商家	⭐⭐⭐	
supplier.isFactoryInspected	是否实地验厂通过	⭐⭐⭐⭐	可靠度高
supplier.isBusinessInspected	是否实地验商通过	⭐⭐⭐⭐	
supplier.certification.type	认证类型	⭐⭐⭐⭐	
supplier.certification.number	认证编号	⭐⭐⭐⭐	可验证
supplier.certification.reportUrl	认证报告链接	⭐⭐⭐⭐	原始报告
supplier.tpYear	平台入驻年限	⭐⭐⭐	
supplier.fans	粉丝数	⭐⭐	
2.9 供应商评分（⭐⭐⭐⭐⭐ 量化信任）
字段	解释	星级	备注
supplier.scores.composite	综合评分(0-5)	⭐⭐⭐⭐⭐	一眼看全貌
supplier.scores.goods	货描相符(0-5)	⭐⭐⭐⭐⭐	实物 vs 图片
supplier.scores.logistics	物流速度(0-5)	⭐⭐⭐⭐	发货效率
supplier.scores.dispute	纠纷处理(0-5)	⭐⭐⭐⭐	售后态度
supplier.scores.return	退货体验(0-5)	⭐⭐⭐⭐	
supplier.scores.consultation	咨询响应(0-5)	⭐⭐⭐	沟通效率
2.10 供应商经营数据（超级工厂增强）
字段	解释	星级	备注
supplier.stats.repeatBuyers	回头客户数	⭐⭐⭐⭐	
supplier.stats.crossBorderBuyers	跨境客户数	⭐⭐⭐⭐⭐	印尼最关心的！
supplier.stats.repeatRate	回头率	⭐⭐⭐⭐	
supplier.stats.positiveReviewRate	好评率	⭐⭐⭐⭐	
supplier.stats.responseRate	响应率	⭐⭐⭐	
supplier.stats.brandPartner	合作品牌	⭐⭐⭐⭐	代工经历
supplier.stats.factoryArea	厂房面积(m²)	⭐⭐⭐⭐	规模实感
supplier.stats.employees	员工人数	⭐⭐⭐⭐	规模实感
supplier.stats.patents	专利数	⭐⭐⭐	研发能力
supplier.stats.mainDevices	主要设备数	⭐⭐⭐	
supplier.stats.scaleTier	企业规模等级	⭐⭐⭐	
supplier.stats.ownBrand	自有品牌名	⭐⭐⭐⭐	
supplier.stats.totalOffers	店铺商品总数	⭐⭐⭐	经营规模
supplier.stats.certifications	认证标签列表	⭐⭐⭐	
2.11 供应商其他
字段	解释	星级	备注
supplier.factoryTags[]	工厂标签	⭐⭐⭐	
supplier.videos[]	工厂视频	⭐⭐⭐	看厂实景
supplier.rank	排行榜排名	⭐⭐⭐	
supplier.originMerchant	源头商家认证	⭐⭐⭐⭐	
supplier.intelligence	增强数据(需付费add-on)	⭐⭐⭐⭐	交易额/收藏数/公司标签
2.12 发货/物流
字段	解释	星级	备注
shipping.deliveryDays	承诺发货天数	⭐⭐⭐⭐	
shipping.deliveryHours	承诺发货小时	⭐⭐⭐⭐	
shipping.logisticsText	物流描述	⭐⭐⭐	如"承诺48小时发货"
shipping.location	发货地	⭐⭐⭐⭐	产业带匹配
shipping.carrier	承运商	⭐⭐	
shipping.postFee	国内运费(CNY)	⭐⭐⭐	
shipping.isFreeShipping	是否包邮	⭐⭐⭐	
shipping.protectionInfos[]	物流保障	⭐⭐	
2.13 代发/分销（需 includeSupplierIntelligence: true）
字段	解释	星级	备注
dropship.enabled	是否支持代发	⭐⭐⭐⭐⭐	一件代发
dropship.consignPrice	代发价	⭐⭐⭐⭐	
dropship.channels[]	授权渠道(淘宝/拼多多/TikTok等)	⭐⭐⭐⭐	
dropship.metrics.orders30d	代发30天订单数	⭐⭐⭐⭐	
dropship.metrics.distributorCount	分销商数量	⭐⭐⭐	
dropship.protections[]	代发保障服务	⭐⭐⭐	
certificates.items[]	产品资质证书	⭐⭐⭐⭐	质检报告/专利
三、Sourcely 当前使用状况
状态	字段
✅ 已用	title, images[0:5], price.min/max, minOrderQuantity, saledCount, wantBuyCount, stock, isOutOfStock, unit, specs[3-5], services[], supplier.companyName, supplier.flags.*, shipping.*
🔴 建议加	supplier.scores.*(量化评分)、supplier.stats.crossBorderBuyers(跨境经验)、supplier.stats.factoryArea+employees(规模实感)、unitWeight(运费精准)、quantityPrices(阶梯价)、supportsSampling(拿样标识)、supplier.foundedYear(经营年限)
⚪ 可忽略	coupons[], promotions[], tags[], supplier.coordinates, supplier.videos[]
结论：Apify 这个 Actor 返回 50+ 字段，Sourcely 目前只用了约 20 个。评分体系(scores)、跨境数据(crossBorderBuyers)、规模数据(factoryArea/employees)、重量(unitWeight)这些已经在返回体里，不额外花钱——只是代码里没映射到前端。