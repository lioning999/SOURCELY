"""三产品字段差异对比"""
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

files = {
    '蒲扇': 'tests/apify_raw_response.json',
    '车载支架': 'tests/apify_raw_response_1059645864166.json',
    '太阳镜': 'tests/apify_raw_response_723736665098.json',
}

DESC = {
    'offerId':'1688商品ID','title':'产品标题','detailUrl':'详情页链接',
    'images[]':'产品图片','videoUrl':'产品视频','descriptionImages[]':'详情图片',
    'descriptionUrl':'详情URL','descriptionText':'详情纯文本',
    'categoryId':'类目ID','topCategoryId':'顶级类目ID','categoryName':'类目名称','categoryPath':'类目全路径',
    'unit':'销售单位','price.min':'最低价','price.max':'最高价','price.currency':'货币',
    'quantityPrices[0].quantityRange':'阶梯价-数量范围','quantityPrices[0].quantityMin':'阶梯价-起批',
    'quantityPrices[0].quantityMax':'阶梯价-上限','quantityPrices[0].price':'阶梯价-单价',
    'specs[0].name':'规格参数名','specs[0].value':'规格参数值',
    'skuImages[0].name':'SKU变体名','skuImages[0].imgUrl':'SKU变体图',
    'saledCount':'累计销量','saledCountStr':'销量展示文案','recentSoldCount':'近期销量',
    'soldDisplay':'平台展示销量','orderCount':'30天订单数','wantBuyCount':'想买人数',
    'stock':'库存','isOutOfStock':'是否断货','unitWeight':'单件重量',
    'minOrderQuantity':'最小起批量','supportsMix':'支持混批',
    'mixWholesale.minAmount':'混批最低金额','mixWholesale.minVarieties':'混批最低品种数',
    'supportsSampling':'支持拿样','isCrossBorderTrade':'跨境贸易通道',
    'customization.supported':'支持定制/OEM','serviceLabels[]':'服务保障标签',
    'promotions[]':'店铺促销','coupons[0].label':'优惠券-标签','coupons[0].summary':'优惠券-摘要',
    'services[0].name':'售后服务-名称','services[0].code':'售后服务-编码','services[0].description':'售后服务-说明',
    'productFlags.isSkuOffer':'多SKU','productFlags.isPreSell':'预售',
    'productFlags.isConsignMarket':'寄售','productFlags.isFreeSample':'免费拿样',
    'productFlags.isBuyerProtection':'买家保障','productFlags.isWeChatSupply':'微信供货',
    'productFlags.isCrossBorder':'跨境专供','productFlags.isOnePiece':'一件代发',
    'productFlags.isWholesale':'批发','productFlags.isToTikTok':'面向TikTok',
    'productFlags.isToKuaiShou':'面向快手','productFlags.isSupportMix':'支持混批(flag)',
    'productFlags.hasRelationOffer':'关联商品','productFlags.isChtSingleOffer':'诚信通单品',
    'productFlags.isDetailForbidden':'禁止查看详情','productFlags.supportsCustomization':'支持定制(flag)',
    'winportUrl':'店铺Winport链接','sourceKeyword':'搜索关键词',
    'purchaseLimits.personalLimit':'个人限购','purchaseLimits.promotionLimit':'促销限购',
    'supplier.memberId':'供应商会员ID','supplier.companyName':'公司名称',
    'supplier.legalCompanyName':'工商注册全名','supplier.loginId':'旺旺登录名','supplier.userId':'用户ID',
    'supplier.foundedYear':'成立年份','supplier.sellerType':'商家等级类型',
    'supplier.bizType':'经营类型','supplier.tpYear':'平台入驻年数',
    'supplier.fans':'粉丝数','supplier.mainCategory':'主营类目',
    'supplier.address':'公司地址','supplier.coordinates':'经纬度',
    'supplier.shopUrl':'店铺首页链接','supplier.imUrl':'旺旺链接',
    'supplier.isOnline':'是否在线','supplier.supportsDistribution':'开通分销',
    'supplier.isFactoryInspected':'实地验厂','supplier.isBusinessInspected':'实地验商',
    'supplier.isSuperFactory':'超级工厂','supplier.featureBadge':'特征标签',
    'supplier.factoryTags[]':'工厂标签','supplier.videos[]':'工厂视频',
    'supplier.rank.text':'排行榜名次','supplier.originMerchant.type':'源头商家类型',
    'supplier.originMerchant.description':'源头商家描述',
    'supplier.certification.type':'认证类型','supplier.certification.number':'认证编号',
    'supplier.certification.reportUrl':'认证报告链接',
    'supplier.stats.repeatBuyers':'回头客户数','supplier.stats.crossBorderBuyers':'跨境买家数',
    'supplier.stats.repeatRate':'回头率','supplier.stats.positiveReviewRate':'好评率',
    'supplier.stats.responseRate':'响应率','supplier.stats.brandPartner':'合作品牌',
    'supplier.stats.factoryArea':'厂房面积','supplier.stats.employees':'员工人数',
    'supplier.stats.patents':'专利数','supplier.stats.mainDevices':'主要设备数',
    'supplier.stats.scaleTier':'企业规模等级','supplier.stats.ownBrand':'自有品牌',
    'supplier.stats.totalOffers':'店铺商品总数','supplier.stats.certifications':'认证资质列表',
    'supplier.stats.rawCardDetail[0].code':'档案卡片编码','supplier.stats.rawCardDetail[0].title':'档案卡片标题',
    'supplier.stats.rawCardDetail[0].info':'档案卡片数值','supplier.stats.rawCardDetail[0].unit':'档案卡片单位',
    'supplier.flags.isFactory':'生产厂家','supplier.flags.isSuperFactory':'超级工厂(flag)',
    'supplier.flags.isTpFactory':'TP验厂通过','supplier.flags.isShiliFactory':'实力工厂',
    'supplier.flags.isSiliCertifiedBrand':'品牌认证','supplier.flags.isChtMember':'诚信通会员',
    'supplier.flags.isFactoryDealer':'厂货通商家','supplier.flags.isYuantouFlagship':'源头旗舰',
    'supplier.flags.isIndustrySeller':'行业商家','supplier.flags.isHyper':'实力商家',
    'supplier.flags.isEaseBuyDealer':'快采商家','supplier.flags.isTp':'第三方认证',
    'supplier.flags.isBrandPlus':'品牌+','supplier.flags.isProcessingTag':'加工标签',
    'supplier.flags.isSmt':'SMT商家','supplier.flags.isImall':'iMall商家',
    'supplier.flags.isFullOnline':'全线上运营','supplier.flags.isTuoguan':'托管模式',
}

def get_val(obj, path):
    keys = path.replace('[]', '').split('.')
    for k in keys:
        if k.endswith('[0]'): k = k[:-3]
        if isinstance(obj, dict): obj = obj.get(k)
        elif isinstance(obj, list) and obj: obj = obj[0] if isinstance(obj[0], dict) else obj
        else: return None
    return obj

def is_null(v):
    return v is None or v == '' or v == []

datas = {}
for name, f in files.items():
    datas[name] = json.loads(open(f, encoding='utf-8').read())

print('===== 三产品字段差异对比 =====\n')

# Three-way comparison
all_ok = []     # all 3 have value
some_null = []   # some null, some not
all_null = []    # all 3 null

for path, desc in sorted(DESC.items()):
    statuses = []
    for name in ['蒲扇','车载支架','太阳镜']:
        v = get_val(datas[name], path)
        statuses.append(not is_null(v))
    n_ok = sum(statuses)
    if n_ok == 3:
        all_ok.append((path, desc))
    elif n_ok == 0:
        all_null.append((path, desc))
    else:
        some_null.append((path, desc, statuses))

print(f'三款全有值: {len(all_ok)} 个')
print(f'三款全NULL: {len(all_null)} 个')
print(f'部分有值:   {len(some_null)} 个')
print()

print('--- 三款全NULL（Apify根本不返回）---')
for path, desc in all_null:
    print(f'  {desc} ({path})')

print()
print('--- 部分有值（店铺差异导致）---')
for path, desc, statuses in some_null:
    names = ['蒲扇','车载支架','太阳镜']
    labels = ['有值' if s else '✗' for s in statuses]
    parts = [f'{n}={l}' for n,l in zip(names, labels)]
    print(f'  {desc} ({path}): {", ".join(parts)}')

print()
print(f'=== 汇总 ===')
print(f'三款全有值(可保留): {len(all_ok)}')
print(f'三款全NULL(可删除): {len(all_null)}')
print(f'部分有值(核心/可选): {len(some_null)}')
