"""生成 1688 产品指标实测表格。"""
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

data = json.loads(open('tests/apify_raw_response.json', encoding='utf-8').read())

DESC = {
    'offerId': '1688商品唯一ID', 'title': '产品标题', 'detailUrl': '商品详情页链接',
    'images[]': '产品图片列表', 'videoUrl': '产品视频链接',
    'descriptionImages[]': '详情描述图片', 'descriptionUrl': '详情页URL',
    'descriptionText': '详情纯文本', 'categoryId': '类目ID', 'topCategoryId': '顶级类目ID',
    'categoryName': '类目名称', 'categoryPath': '类目全路径', 'unit': '销售单位',
    'price.min': '最低价(CNY)', 'price.max': '最高价(CNY)', 'price.currency': '货币',
    'quantityPrices[]': '阶梯批发价', 'specs[]': '规格参数', 'skuImages[]': 'SKU规格图片',
    'saledCount': '累计销量', 'saledCountStr': '销量展示文本', 'recentSoldCount': '近期销量',
    'soldDisplay': '平台展示销量', 'orderCount': '30天订单数', 'wantBuyCount': '想买人数',
    'stock': '库存量', 'isOutOfStock': '是否断货', 'unitWeight': '单件重量(kg)',
    'minOrderQuantity': '最小起批量', 'supportsMix': '是否支持混批',
    'mixWholesale.minAmount': '混批最低金额', 'mixWholesale.minVarieties': '混批最低品种数',
    'supportsSampling': '是否支持拿样', 'isCrossBorderTrade': '是否跨境贸易',
    'customization.supported': '是否支持定制/OEM', 'serviceLabels[]': '服务标签',
    'promotions[]': '店铺促销', 'coupons[]': '商品优惠券', 'services[]': '售后服务',
    'productFlags.isSkuOffer': '是否有SKU', 'productFlags.isPreSell': '是否预售',
    'productFlags.isFreeSample': '是否支持免费拿样',
    'productFlags.isBuyerProtection': '是否有买家保障',
    'productFlags.isCrossBorder': '是否跨境专供', 'productFlags.isOnePiece': '是否一件代发',
    'productFlags.isWholesale': '是否批发', 'productFlags.isToTikTok': '是否面向TikTok',
    'productFlags.isToKuaiShou': '是否面向快手', 'productFlags.isSupportMix': '是否支持混批',
    'productFlags.hasRelationOffer': '是否有关联商品',
    'productFlags.isDetailForbidden': '是否禁止查看详情',
    'productFlags.supportsCustomization': '是否支持定制',
    'productFlags.isConsignMarket': '是否寄售', 'productFlags.isWeChatSupply': '是否微信供货',
    'productFlags.isChtSingleOffer': '是否诚信通单品', 'winportUrl': '店铺Winport链接',
    'purchaseLimits.personalLimit': '个人限购', 'purchaseLimits.promotionLimit': '促销限购',
    # supplier
    'supplier.memberId': '供应商会员ID', 'supplier.companyName': '公司名',
    'supplier.legalCompanyName': '工商注册全名', 'supplier.loginId': '登录名',
    'supplier.foundedYear': '成立年份', 'supplier.province': '省份', 'supplier.city': '城市',
    'supplier.address': '完整地址', 'supplier.sellerType': '商家类型',
    'supplier.bizType': '经营类型', 'supplier.tpYear': '平台入驻年限',
    'supplier.fans': '粉丝数', 'supplier.mainCategory': '主营类目',
    'supplier.shopUrl': '店铺首页链接', 'supplier.imUrl': '旺旺聊天链接',
    'supplier.isOnline': '是否在线', 'supplier.supportsDistribution': '是否支持分销',
    'supplier.isFactoryInspected': '是否实地验厂', 'supplier.isBusinessInspected': '是否实地验商',
    'supplier.isSuperFactory': '是否超级工厂', 'supplier.featureBadge': '信任标签',
    'supplier.factoryTags[]': '工厂标签', 'supplier.videos[]': '工厂视频',
    'supplier.rank.text': '排行榜名次', 'supplier.originMerchant.type': '源头商家类型',
    'supplier.originMerchant.description': '源头商家描述',
    'supplier.certification.type': '企业认证类型', 'supplier.certification.number': '认证编号',
    'supplier.certification.reportUrl': '认证报告链接',
    'supplier.stats.repeatBuyers': '回头客户数',
    'supplier.stats.crossBorderBuyers': '跨境客户数',
    'supplier.stats.repeatRate': '回头率', 'supplier.stats.positiveReviewRate': '好评率',
    'supplier.stats.responseRate': '响应率', 'supplier.stats.brandPartner': '合作品牌',
    'supplier.stats.factoryArea': '厂房面积(m²)', 'supplier.stats.employees': '员工人数',
    'supplier.stats.patents': '专利数', 'supplier.stats.mainDevices': '主要设备数',
    'supplier.stats.scaleTier': '企业规模等级', 'supplier.stats.ownBrand': '自有品牌',
    'supplier.stats.totalOffers': '店铺商品总数',
    'supplier.flags.isFactory': '是否生产厂家', 'supplier.flags.isSuperFactory': '是否超级工厂',
    'supplier.flags.isTpFactory': '是否TP验厂', 'supplier.flags.isShiliFactory': '是否实力工厂',
    'supplier.flags.isSiliCertifiedBrand': '是否品牌认证',
    'supplier.flags.isChtMember': '是否诚信通会员', 'supplier.flags.isFactoryDealer': '是否厂货通',
    'supplier.flags.isYuantouFlagship': '是否源头旗舰',
    'supplier.flags.isIndustrySeller': '是否行业商家', 'supplier.flags.isHyper': '是否实力商家',
    'supplier.flags.isTp': '是否第三方认证', 'supplier.flags.isEaseBuyDealer': '是否快采商家',
    'supplier.flags.isProcessingTag': '是否加工标签', 'supplier.flags.isSmt': '是否SMT',
    'supplier.flags.isBrandPlus': '是否品牌+', 'supplier.flags.isTuoguan': '是否托管',
    # shipping
    'shipping.deliveryHours': '承诺发货小时', 'shipping.deliveryDays': '承诺发货天数',
    'shipping.carrier': '承运快递', 'shipping.logisticsText': '物流描述',
    'shipping.location': '发货地', 'shipping.postFee': '国内运费(CNY)',
    'shipping.isFreeShipping': '是否包邮', 'shipping.unitWeight': '单件重量(kg)',
    'shipping.templateRemark': '运费模板说明', 'shipping.protectionInfos[0].name': '物流保障',
    # dropship
    'dropship.enabled': '是否支持代发', 'dropship.consignPrice': '代发价',
    'dropship.channels[]': '授权渠道列表',
    'dropship.metrics.orders30d': '代发30天单量', 'dropship.metrics.distributorCount': '分销商数量',
}

def get_val(obj, path):
    keys = path.replace('[]', '').split('.')
    for k in keys:
        if k.endswith('[0]'):
            k = k[:-3]
        if isinstance(obj, dict):
            obj = obj.get(k)
        elif isinstance(obj, list) and obj:
            obj = obj[0] if isinstance(obj[0], dict) else obj
        else:
            return None
    return obj

def fmt_val(v, path=''):
    if v is None: return '-'
    if isinstance(v, bool): return '是' if v else '否'
    if isinstance(v, list):
        if not v: return '-'
        if isinstance(v[0], str): return ', '.join([str(x)[:40] for x in v[:3]])
        return f'[{len(v)}项]'
    if isinstance(v, float):
        if 'Rate' in path or 'rate' in path:
            return f'{v*100:.1f}%'
        return f'{v}'
    s = str(v)[:100]
    return s

rows = []
for path in sorted(DESC.keys()):
    if path.startswith('supplier.'):
        group = '供应商'
    elif path.startswith('shipping.'):
        group = '物流'
    elif path.startswith('dropship.'):
        group = '代发'
    else:
        group = '产品'
    desc = DESC[path]
    val = get_val(data, path)
    val_str = fmt_val(val, path)
    rows.append((group, path, val_str, desc))

lines = []
lines.append('# 1688 Wholesale Scraper — 实测返回指标')
lines.append('')
lines.append(f'> 测试商品：[卡通可爱手编织小蒲扇](https://detail.1688.com/offer/1038913113865.html)  ')
lines.append(f'> 供应商：义乌市雨灏贸易有限公司 | 测试时间：2026-07-20  ')
lines.append(f'> 数据来源：Apify `zen-studio/1688-wholesale-scraper` 实测（非文档推测）')
lines.append('')
lines.append('| 分类 | 字段 | 真实值 | 中文描述 |')
lines.append('|------|------|--------|----------|')
cur = ''
for group, path, val_str, desc in rows:
    if group != cur:
        cur = group
        lines.append(f'| **{group}** | | | |')
    lines.append(f'| | `{path}` | {val_str} | {desc} |')

out = '\n'.join(lines)
open('tests/1688产品指标-实测.md', 'w', encoding='utf-8').write(out)
print(f'Done: {len(rows)} 行 → tests/1688产品指标-实测.md')
