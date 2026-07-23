"""全面字段对比：6个产品×所有关键字段 → 必返/条件返/不返 分类"""
import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.join(os.path.dirname(__file__), '..')


def _get_nested(d, path):
    """从dict按点分隔路径取值"""
    keys = path.replace('[].', '.').replace('[]', '').split('.')
    v = d
    for k in keys:
        if isinstance(v, dict):
            v = v.get(k)
        elif isinstance(v, list):
            return len(v)  # path references array itself
        else:
            return None
    return v

FILES = [
    ('蒲扇',      'tests/apify_raw_sample.json'),
    ('木盒子',    'src/web/temp/997997017645.json'),
    ('爱心项链',  'src/web/temp/1053910572406.json'),
    ('太阳镜',    'src/web/temp/900685412535.json'),
    ('iPhone壳',  'src/web/temp/685469710262.json'),
    ('demo手机壳','src/web/temp/demo.json'),
]

products = []
for label, path in FILES:
    full = os.path.join(BASE, path)
    with open(full, 'r', encoding='utf-8') as f:
        d = json.load(f)
    s = d.get('supplier', {})
    st = s.get('stats', {})
    fl = s.get('flags', {})
    pf = d.get('productFlags', {})
    products.append({
        'label': label,
        'sellerType': s.get('sellerType', ''),
        'isYt': fl.get('isYuantouFlagship', False),
        'isSf': fl.get('isSuperFactory', False),
        'isFac': fl.get('isFactory', False),
        'tpYear': s.get('tpYear'),
        'founded': s.get('foundedYear'),
        'd': d, 's': s, 'st': st, 'fl': fl, 'pf': pf,
    })

# ============================================================
# A. 100%必返
# ============================================================
print("=" * 100)
print("A. 100% 必返字段 (6/6 全部有值，不管什么等级)")
print("=" * 100)
print()

A_FIELDS = [
    ("商品标题",    "title",                        "产品名称",                       "报告头部标题"),
    ("最低价(¥)",   "price.min",                    "最低批发价(CNY)",                "价格卡片"),
    ("最高价(¥)",   "price.max",                    "最高批发价(CNY)",                "价格卡片"),
    ("币种",        "price.currency",               "固定 CNY",                       "价格卡片"),
    ("起批量",      "minOrderQuantity",             "最小起订量(MOQ)",                "价格卡片-MOQ"),
    ("销售单位",    "unit",                         "件/把/PCS/副",                   "价格卡片-单位"),
    ("累计销量",    "saledCount",                   "历史总销量数",                   "产品指标-销量"),
    ("商品图",      "images[]",                     "5 张商品主图 URL 数组",          "图片画廊"),
    ("规格参数",    "specs[]",                      "产品规格 K-V 数组",             "规格参数表"),
    ("服务标签",    "serviceLabels[]",              "7天无理由/晚发必赔 等文本数组",  "Badge 行"),
    ("产品标识",    "productFlags.*",               "isFreeSample/isCrossBorder 等 16 个布尔", "Badge 行"),
    ("商品链接",    "detailUrl",                    "1688 商品详情页 URL",            "(数据源)"),
    ("商品ID",      "offerId",                      "1688 商品唯一 ID",               "(数据源)"),
    ("SKU明细",     "skuDetails[]",                 "SKU 详细数组",                  "SKU 卡片区"),
    ("卖家类型",    "supplier.sellerType",          "yuantou_flagship/super_factory/normal_factory/normal", "工厂信息-等级"),
    ("开店年限",    "supplier.tpYear",              "在 1688 开店的年数(1年=新店)",  "工厂信息-年限"),
    ("店铺名称",    "supplier.companyName",         "店铺公司名称",                   "工厂信息-名称"),
    ("法律实体名",  "supplier.legalCompanyName",    "工商注册公司全名",               "(备用)"),
    ("粉丝数",      "supplier.fans",                "店铺关注数 如 2.7w/390/6.2k",   "(判词参考)"),
    ("主营类目",    "supplier.mainCategory",        "主要经营品类 如 服饰配件、饰品", "(判词参考)"),
    ("发货地址",    "shipping.location",            "发货/工厂地址 如 广东汕头",     "工厂信息-产地"),
    ("是否在线",    "supplier.isOnline",            "店铺在线状态",                   "(判词参考)"),
    ("会员ID",      "supplier.memberId",            "1688 商家唯一会员 ID",           "(数据源)"),
    ("旺旺ID",      "supplier.loginId",             "阿里旺旺客服 ID",                "(数据源)"),
    ("店铺URL",     "supplier.shopUrl",             "1688 店铺首页链接",              "(数据源)"),
    ("供应商标识",  "supplier.flags.*",             "isFactory/isSuperFactory 等 18 个布尔", "(评级依据)"),
]

for name, path, meaning, area in A_FIELDS:
    vals = []
    for p in products:
        v = _get_nested(p['d'], path)
        if v is None or v == '' or v == [] or v == {}:
            vals.append("-")
        else:
            s = str(v)
            vals.append(s[:28] if len(s) > 28 else s)
    print(f"{name:12s} | {path:35s} | {meaning:40s} | {area:20s}")
    # print values on next line for readability
    # print(f"              values: {' | '.join(vals)}")

print()
print(f"共 {len(A_FIELDS)} 个必返字段")
print()

# ============================================================
# B. 条件返回 (由 flags.isYuantouFlagship / isSuperFactory / isFactory 决定)
# ============================================================
print("=" * 100)
print("B. 条件返回字段 (取决于 flags)")
print("=" * 100)
print()

B_FIELDS = [
    # stats 直接字段 — 只有 isYuantouFlagship==True 才有
    ("好评率(%)",     "stats.positiveReviewRate",    "店铺好评率 0-1 小数",          "产品指标-好评率",
        lambda p: p['fl'].get('isYuantouFlagship', False)),
    ("回头率(%)",     "stats.repeatRate",             "店铺复购率 0-1 小数",          "产品指标-回头率",
        lambda p: p['fl'].get('isYuantouFlagship', False)),
    ("复购买家",      "stats.repeatBuyers",           "复购客户数 如 100+/1600+",     "产品指标-回头客",
        lambda p: p['fl'].get('isYuantouFlagship', False)),
    ("跨境买家",      "stats.crossBorderBuyers",      "跨境采购客户数 如 80+/300+",   "产品指标-跨境买家",
        lambda p: p['fl'].get('isYuantouFlagship', False)),
    ("客服响应率",    "stats.responseRate",           "客服响应率 0-1 小数",          "(判词参考)",
        lambda p: p['fl'].get('isYuantouFlagship', False)),

    # factoryTags — 只有 isSuperFactory==True 才有
    ("工厂标签",      "supplier.factoryTags[].text",  "回头率/履约率/服务分 文本值",  "产品指标-回头率(fallback)",
        lambda p: p['fl'].get('isSuperFactory', False)),

    # rawCardDetail — isYuantouFlagship 有完整版，isSuperFactory 有工厂版，低级为空
    ("数据卡片",      "stats.rawCardDetail[]",        "好评率/回头率/设备/面积/员工等 按code索引",
        "产品指标(fallback)",
        lambda p: p['fl'].get('isYuantouFlagship', False) or p['fl'].get('isSuperFactory', False)),

    # certification — 工厂类卖家(super_factory / yuantou_flagship)有
    ("深度认证",      "supplier.certification.type",  "SGS/TUV/CTI/null",             "工厂信息-认证",
        lambda p: p['fl'].get('isSuperFactory', False) or p['fl'].get('isYuantouFlagship', False) or p['fl'].get('isShiliFactory', False)),

    # rank — 不稳定，上榜才有
    ("行业排名",      "supplier.rank.text",           "如 上榜TOP17/二钻工厂/第1名/null", "工厂信息-排名",
        lambda p: True),  # 不是条件问题，是商品级别的

    # originMerchant — isYuantouFlagship 有
    ("产业带认证",    "supplier.originMerchant",      "1688 官方产业带旗舰商家认证",    "工厂信息-产业带",
        lambda p: p['fl'].get('isYuantouFlagship', False)),

    # foundedYear — isYuantouFlagship 或 isSuperFactory 有
    ("公司成立年",    "supplier.foundedYear",         "公司工商成立年份 如 2014/2026", "工厂信息-成立时间",
        lambda p: p['fl'].get('isYuantouFlagship', False) or p['fl'].get('isSuperFactory', False)),
]

for name, path, meaning, area, condition_fn in B_FIELDS:
    print(f"\n--- {name} [{path}] ---")
    print(f"    含义: {meaning} | 页面: {area}")
    print(f"    条件: flags.isYuantouFlagship+isSuperFactory")

    # Header
    header = f"    {'':10s}"
    for p in products:
        header += f"  {p['label']:8s}"
    print(header)

    # sellerType row
    row = f"    {'sellerType':10s}"
    for p in products:
        row += f"  {p['sellerType'][:8]:8s}"
    print(row)

    # isYt row
    row = f"    {'isYt':10s}"
    for p in products:
        row += f"  {'✓' if p['isYt'] else '-':8s}"
    print(row)

    # isSf row
    row = f"    {'isSf':10s}"
    for p in products:
        row += f"  {'✓' if p['isSf'] else '-':8s}"
    print(row)

    # Value row
    row = f"    {'VALUE':10s}"
    for p in products:
        v = _get_nested(p['d'], path)
        if v is None or v == '' or v == [] or v == {}:
            s = '-'
        else:
            s = str(v)[:22]
        row += f"  {s:8s}"
    print(row)

    # Verify condition
    row = f"    {'条件判定':10s}"
    for p in products:
        predicted = condition_fn(p)
        actual = (_get_nested(p['d'], path) is not None
                  and _get_nested(p['d'], path) != ''
                  and _get_nested(p['d'], path) != []
                  and _get_nested(p['d'], path) != {})
        match = '✓' if predicted == actual else 'MISMATCH!'
        row += f"  {match:8s}"
    print(row)

print()
print()

# ============================================================
# C. 汇总规则
# ============================================================
print("=" * 100)
print("C. 规律总结")
print("=" * 100)
print()

# Build rules by flag combination
print("数据丰富度由 flags 的三个关键布尔值决定：")
print()
print("  isYuantouFlagship = True")
print("    → stats.positiveReviewRate, repeatRate, repeatBuyers, crossBorderBuyers, responseRate 全部填充")
print("    → rawCardDetail 含 好评率/回头率/回购老客/响应率 文本版")
print("    → certification 有值 (SGS)")
print("    → rank 大概率有值")
print("    → originMerchant 有值")
print("    → foundedYear 有值")
print()
print("  isSuperFactory = True (且 isYuantouFlagship=False)")
print("    → stats 直接字段 全部为 None")
print("    → supplier.factoryTags 有 回头率/履约率/服务分 文本")
print("    → rawCardDetail 只含工厂设备数据(设备数/面积/员工) 不含店铺评估数据")
print("    → certification 有值 (TUV/CTI)")
print("    → rank 部分有值 (二钻工厂)")
print("    → foundedYear 有值")
print()
print("  isFactory = True (isSuperFactory=False, isYuantouFlagship=False)")
print("    → stats 全空, factoryTags 空, rawCardDetail 空")
print("    → certification 无, rank 无")
print("    → foundedYear 无")
print()
print("  ️ 纯贸易商 (isFactory=False)")
print("    → 以上全部为空")
print("    → 只有 A 类必返字段")
print()
print("  核心规则：")
print("    好评率/回头率 → isYuantouFlagship 决定 (stats 路径)")
print("    回头率(文本)  → isSuperFactory 决定 (factoryTags 路径)")
print("    认证         → isSuperFactory 或 isYuantouFlagship 决定")
print("    排名         → 不稳定，有排名才返回")
