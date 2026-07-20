"""通用版 gen_html — 从 JSON 生成产品指标查看页面"""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('json_file')
parser.add_argument('--out', default=None)
args = parser.parse_args()

data = json.loads(open(args.json_file, encoding='utf-8').read())
out_file = args.out or args.json_file.replace('.json', '.html')

DESC = {
    'offerId': '1688商品ID', 'title': '产品标题', 'detailUrl': '商品详情页链接',
    'images[]': '产品图片列表', 'videoUrl': '产品视频', 'descriptionImages[]': '详情描述图片',
    'descriptionUrl': '详情页URL', 'descriptionText': '详情纯文本',
    'categoryId': '类目ID', 'topCategoryId': '顶级类目ID', 'categoryName': '类目名称', 'categoryPath': '类目全路径',
    'unit': '销售单位', 'price.min': '最低价(CNY)', 'price.max': '最高价(CNY)', 'price.currency': '货币',
    'quantityPrices[0].quantityRange': '阶梯批发价-数量范围', 'quantityPrices[0].quantityMin': '阶梯批发价-起批',
    'quantityPrices[0].quantityMax': '阶梯批发价-上限', 'quantityPrices[0].price': '阶梯批发价-单价(CNY)',
    'specs[0].name': '规格参数名(例)', 'specs[0].value': '规格参数值(例)',
    'skuImages[0].name': 'SKU变体图-名称', 'skuImages[0].imgUrl': 'SKU变体图-链接',
    'saledCount': '累计销量(件)', 'saledCountStr': '销量展示文案', 'recentSoldCount': '近期销量',
    'soldDisplay': '平台展示销量', 'orderCount': '30天订单数', 'wantBuyCount': '想买人数',
    'stock': '当前库存', 'isOutOfStock': '是否已断货', 'unitWeight': '单件重量(kg)',
    'minOrderQuantity': '最小起批量', 'supportsMix': '是否支持混批',
    'mixWholesale.minAmount': '混批最低金额(CNY)', 'mixWholesale.minVarieties': '混批最低品种数',
    'supportsSampling': '是否支持拿样', 'isCrossBorderTrade': '是否跨境贸易通道',
    'customization.supported': '是否支持定制/贴牌(OEM)', 'serviceLabels[]': '服务保障标签列表',
    'promotions[]': '店铺促销活动', 'coupons[0].type': '优惠券-类型',
    'coupons[0].label': '优惠券-标签', 'coupons[0].summary': '优惠券-摘要',
    'services[0].name': '售后服务-名称', 'services[0].code': '售后服务-编码',
    'services[0].description': '售后服务-说明',
    'productFlags.isSkuOffer': '多SKU商品', 'productFlags.isPreSell': '是否预售商品',
    'productFlags.isConsignMarket': '是否寄售商品', 'productFlags.isFreeSample': '是否支持免费拿样',
    'productFlags.isBuyerProtection': '是否有买家保障', 'productFlags.isWeChatSupply': '是否微信供货',
    'productFlags.isCrossBorder': '是否跨境专供', 'productFlags.isOnePiece': '是否一件代发',
    'productFlags.isWholesale': '是否批发商品', 'productFlags.isToTikTok': '是否面向TikTok渠道',
    'productFlags.isToKuaiShou': '是否面向快手渠道', 'productFlags.isSupportMix': '是否支持混批',
    'productFlags.hasRelationOffer': '是否有关联商品', 'productFlags.isChtSingleOffer': '是否诚信通单品',
    'productFlags.isDetailForbidden': '是否禁止查看详情', 'productFlags.supportsCustomization': '是否支持定制',
    'winportUrl': '店铺Winport链接', 'sourceKeyword': '搜索关键词',
    'purchaseLimits.personalLimit': '个人限购数量', 'purchaseLimits.promotionLimit': '促销限购数量',
    # supplier
    'supplier.memberId': '供应商会员ID', 'supplier.companyName': '公司名称',
    'supplier.legalCompanyName': '工商注册全名', 'supplier.loginId': '旺旺登录名', 'supplier.userId': '用户ID',
    'supplier.foundedYear': '成立年份', 'supplier.sellerType': '1688商家等级类型',
    'supplier.bizType': '经营类型(生产加工/经销批发)', 'supplier.tpYear': '平台入驻年数',
    'supplier.fans': '店铺粉丝数', 'supplier.mainCategory': '主营类目',
    'supplier.address': '公司地址', 'supplier.coordinates': '经纬度',
    'supplier.shopUrl': '店铺首页链接', 'supplier.imUrl': '旺旺聊天链接',
    'supplier.isOnline': '当前是否在线', 'supplier.supportsDistribution': '是否开通分销',
    'supplier.isFactoryInspected': '是否通过实地验厂', 'supplier.isBusinessInspected': '是否通过实地验商',
    'supplier.isSuperFactory': '是否超级工厂', 'supplier.featureBadge': '特征标签',
    'supplier.factoryTags[]': '工厂标签列表', 'supplier.videos[]': '工厂视频列表',
    'supplier.rank.text': '1688排行榜名次', 'supplier.originMerchant.type': '源头商家类型',
    'supplier.originMerchant.description': '源头商家描述',
    'supplier.certification.type': '企业认证类型(SGS/ISO等)', 'supplier.certification.number': '企业认证编号',
    'supplier.certification.reportUrl': '企业认证报告链接',
    'supplier.stats.repeatBuyers': '回头客户数', 'supplier.stats.crossBorderBuyers': '跨境买家数',
    'supplier.stats.repeatRate': '回购率(回头率)', 'supplier.stats.positiveReviewRate': '好评率',
    'supplier.stats.responseRate': '卖家响应率', 'supplier.stats.brandPartner': '品牌合作伙伴',
    'supplier.stats.factoryArea': '厂房面积(m²)', 'supplier.stats.employees': '员工人数',
    'supplier.stats.patents': '专利数', 'supplier.stats.mainDevices': '主要设备数',
    'supplier.stats.scaleTier': '企业规模等级', 'supplier.stats.ownBrand': '自有品牌名称',
    'supplier.stats.totalOffers': '店铺商品总数', 'supplier.stats.certifications': '认证资质列表',
    'supplier.stats.rawCardDetail[0].code': '档案卡片编码', 'supplier.stats.rawCardDetail[0].title': '档案卡片标题',
    'supplier.stats.rawCardDetail[0].info': '档案卡片数值', 'supplier.stats.rawCardDetail[0].unit': '档案卡片单位',
    'supplier.flags.isFactory': '是否生产厂家', 'supplier.flags.isSuperFactory': '是否超级工厂',
    'supplier.flags.isTpFactory': '是否TP验厂通过', 'supplier.flags.isShiliFactory': '是否实力工厂',
    'supplier.flags.isSiliCertifiedBrand': '是否品牌认证', 'supplier.flags.isChtMember': '是否诚信通会员',
    'supplier.flags.isFactoryDealer': '是否厂货通商家', 'supplier.flags.isYuantouFlagship': '是否源头旗舰',
    'supplier.flags.isIndustrySeller': '是否行业商家', 'supplier.flags.isHyper': '是否实力商家',
    'supplier.flags.isEaseBuyDealer': '是否快采商家', 'supplier.flags.isTp': '是否第三方认证',
    'supplier.flags.isBrandPlus': '是否品牌+', 'supplier.flags.isProcessingTag': '是否有加工标签',
    'supplier.flags.isSmt': '是否SMT商家', 'supplier.flags.isImall': '是否iMall商家',
    'supplier.flags.isFullOnline': '是否全线上运营', 'supplier.flags.isTuoguan': '是否托管模式',
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

def fmt(v, path=''):
    if v is None: return ('<span class="n">null</span>', 'n')
    if isinstance(v, bool):
        return ('<span class="yes">是</span>', 'ok') if v else ('<span class="no">否</span>', 'no')
    if isinstance(v, list):
        if not v: return ('<span class="n">空数组</span>', 'n')
        if len(v) > 0 and isinstance(v[0], str):
            imgs = ''.join(f'<img src="{x}" loading="lazy" style="max-width:56px;max-height:56px;border-radius:4px;margin:2px;border:1px solid #eee;object-fit:contain;background:#fafafa">' for x in v[:8])
            return (f'<div style="display:flex;flex-wrap:wrap;gap:2px">{imgs}</div><small style="color:#9AA1AC;font-size:10px">共{len(v)}张</small>', 'img')
        return (f'<span class="num">[{len(v)}项]</span>', 'ok')
    if isinstance(v, (int, float)):
        if isinstance(v, float) and 'Rate' in path:
            return (f'<span class="num">{v*100:.1f}%</span>', 'ok')
        s = f'{v:,}' if isinstance(v, int) and abs(v) > 999 else str(v)
        return (f'<span class="num">{s}</span>', 'ok')
    s = str(v)
    if len(s) > 100: s = s[:97]+'...'
    if s.startswith('http'):
        return (f'<a href="{s}" target="_blank" style="font-size:10px">{s[:55]}...</a>', 'url')
    if s == '': return ('<span class="n">空字符串</span>', 'n')
    return (f'<span>{s}</span>', 'ok')

def classify(path):
    if path.startswith('supplier.'): return '供应商'
    return '产品'

items = []
for path, desc in DESC.items():
    val = get_val(data, path)
    if val is None or val == '' or val == []:
        continue
    items.append((path, val, desc, classify(path)))

groups = {'产品': [], '供应商': []}
for path, val, desc, g in items:
    groups[g].append((path, val, desc))

main_imgs = (data.get('images') or [])[:5]
supplier = data.get('supplier') or {}
price = data.get('price') or {}
title = data.get('title','')

html = f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>1688实测返回指标 — {title[:40]}</title>
<style>
:root{{--ok:#2F8A5B;--bad:#D6432F;--line:#E8E4D8;--bg:#FDFBF6;--card:#FFF;--brand:#2A4C78}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:#232A38;max-width:740px;margin:0 auto;padding:16px;line-height:1.5}}
h1{{font-size:18px;margin:0 0 6px}}
.meta{{font-size:11px;color:#9AA1AC;margin-bottom:14px;line-height:1.6}}
.meta a{{color:var(--brand)}}
.preview{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:14px;display:flex;gap:14px;align-items:flex-start}}
.preview img.main{{width:140px;height:140px;object-fit:contain;border-radius:8px;border:1px solid #eee;background:#FAFAFA;flex-shrink:0}}
.preview h3{{font-size:15px;margin:0 0 6px;line-height:1.35}}
.specs{{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0}}
.specs span{{font-size:10px;padding:2px 8px;border-radius:10px;background:#EBF1F8;color:var(--brand);font-weight:600}}
.pr{{font-size:21px;font-weight:700;color:var(--bad);margin:4px 0 2px}}
.pr2{{font-size:11px;color:#9AA1AC}}
.quick{{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px}}
.quick span{{font-size:10px;padding:3px 9px;border-radius:6px;font-weight:600}}
.qok{{background:#E9F6EF;color:var(--ok)}} .qno{{background:#FDEEEB;color:var(--bad)}} .qw{{background:#FBF2DE;color:#B4832E}}
.group{{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:10px;overflow:hidden}}
.ghead{{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;background:#F8F6F0;border-bottom:1px solid var(--line);cursor:pointer;user-select:none}}
.ghead h2{{font-size:13px;margin:0}}.stats{{font-size:10px;color:#9AA1AC;display:flex;gap:10px}}
.sok{{color:var(--ok);font-weight:700}}
.gbody{{padding:0}}.gbody.collapsed{{display:none}}
.row{{display:flex;border-bottom:1px solid #F5F2EC;font-size:11px}}
.row:last-child{{border:none}}.row:hover{{background:#FAFAF7}}
.c1{{width:34%;padding:5px 10px;font-family:'JetBrains Mono',monospace;font-size:9.5px;color:#5B6373;word-break:break-all}}
.c2{{flex:1;padding:5px 8px;font-size:10px;word-break:break-all;display:flex;align-items:center;gap:4px;flex-wrap:wrap}}
.c3{{width:24%;padding:5px 10px;font-size:10px;color:#9AA1AC;display:flex;align-items:center}}
.n{{color:var(--bad);font-style:italic;font-size:9px}}.yes{{font-weight:700;color:var(--ok)}}.no{{color:var(--bad);font-weight:700}}
.num{{color:var(--brand);font-weight:600}}
.legend{{display:flex;gap:14px;font-size:10px;color:#9AA1AC;margin-bottom:12px}}
.dot{{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:4px}}
.dok{{background:var(--ok)}}
</style>
</head>
<body>
<h1>1688 Wholesale Scraper — 实测返回指标</h1>
<div class="meta">
测试商品: <a href="{data.get('detailUrl','#')}" target="_blank">{title}</a><br>
供应商: {supplier.get('companyName','')} | offerId: {data.get('offerId','')} | 2026-07-20<br>
数据来源: Apify <code>zen-studio/1688-wholesale-scraper</code> 实测 | <a href="{args.json_file}">原始JSON</a>
</div>

<div class="preview">
'''

if main_imgs:
    html += f'<img class="main" src="{main_imgs[0]}" alt="主图">'

specs_html = ''
for s in (data.get('specs') or [])[:6]:
    specs_html += f'<span>{s.get("name","")}: {s.get("value","")}</span>'

flags = data.get('productFlags') or {}
quick_tags = []
if flags.get('isCrossBorder'): quick_tags.append('<span class="qok">跨境专供</span>')
else: quick_tags.append('<span class="qno">非跨境</span>')
if flags.get('isFreeSample'): quick_tags.append('<span class="qok">免费拿样</span>')
if flags.get('isBuyerProtection'): quick_tags.append('<span class="qok">买家保障</span>')
if data.get('supportsSampling'): quick_tags.append('<span class="qok">支持拿样</span>')
if data.get('supportsMix'): quick_tags.append('<span class="qw">支持混批</span>')
if not data.get('isOutOfStock'): quick_tags.append('<span class="qok">有库存</span>')

html += f'''<div style="flex:1;min-width:0">
<h3>{title}</h3>
<div class="specs">{specs_html}</div>
<div class="pr">¥{price.get("min","?")} – ¥{price.get("max","?")} <small style="font-size:12px;color:#5B6373">/ {data.get("unit","件")}</small></div>
<div class="pr2">MOQ {data.get("minOrderQuantity",0)}件 | 销量 {data.get("saledCountStr","?")} | 库存 {data.get("stock",0):,} | 想买 {data.get("wantBuyCount",0):,}人</div>
<div class="quick">{''.join(quick_tags)}</div>
'''

if len(main_imgs) > 1:
    html += '<div style="display:flex;gap:4px;margin-top:8px">'
    for u in main_imgs[1:]:
        html += f'<img src="{u}" style="width:44px;height:44px;object-fit:cover;border-radius:4px;border:1px solid #eee" loading="lazy">'
    html += '</div>'

html += '</div></div>'

html += '<div class="legend"><span><span class="dot dok"></span>有值</span>点击分组标题折叠</div>'

for gname in ['产品', '供应商']:
    gitems = groups[gname]
    oks = len(gitems)
    html += f'''<div class="group">
<div class="ghead" onclick="var b=this.nextElementSibling;b.classList.toggle('collapsed');this.querySelector('small').textContent=b.classList.contains('collapsed')?'▶':'▼'">
<h2><small>▼</small> {gname}</h2>
<div class="stats"><span class="sok">{oks} 有值</span></div></div>
<div class="gbody">'''
    for path, val, desc in gitems:
        v_html, v_type = fmt(val, path)
        badge = '<span style="font-size:9px;padding:1px 5px;border-radius:6px;font-weight:700;background:#E9F6EF;color:var(--ok)">OK</span>'
        if v_type == 'no':
            badge = '<span style="font-size:9px;padding:1px 5px;border-radius:6px;font-weight:700;background:#FDEEEB;color:var(--bad)">否</span>'
        html += f'<div class="row"><div class="c1">{path}</div><div class="c2">{v_html}{badge}</div><div class="c3">{desc}</div></div>'
    html += '</div></div>'

html += '</body></html>'

open(out_file, 'w', encoding='utf-8').write(html)
total = sum(len(v) for v in groups.values())
print(f'OK: {total} fields (产品:{len(groups["产品"])} 供应商:{len(groups["供应商"])}) -> {out_file}')
