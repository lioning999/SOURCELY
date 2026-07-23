"""纯数据对比 — 不改代码，只输出表格"""
import json, os

BASE = os.path.join(os.path.dirname(__file__), '..')

files = {
    '蒲扇(旗舰)':      'tests/apify_raw_sample.json',
    '木盒子(super)':   'src/web/temp/997997017645.json',
    '项链(super)':     'src/web/temp/1053910572406.json',
    '太阳镜(normal工)':'src/web/temp/900685412535.json',
    'iPhone壳(normal)':'src/web/temp/685469710262.json',
    'demo壳(super+旗)':'src/web/temp/demo.json',
}

prods = {}
for name, path in files.items():
    with open(os.path.join(BASE, path), 'r', encoding='utf-8') as f:
        d = json.load(f)
    s = d.get('supplier', {})
    st = s.get('stats', {})
    fl = s.get('flags', {})
    pf = d.get('productFlags', {})
    prods[name] = {
        'yt': fl.get('isYuantouFlagship', False),
        'sf': fl.get('isSuperFactory', False),
        'fac': fl.get('isFactory', False),
        'shop_years': s.get('tpYear'),
        'founded': s.get('foundedYear'),
        'fans': s.get('fans'),
        'legalName': s.get('legalCompanyName'),
        'title': (d.get('title') or '')[:35],
        'price_min': d.get('price', {}).get('min'),
        'moq': d.get('minOrderQuantity'),
        'sold': d.get('saledCount'),
        'unit': d.get('unit'),
        'imgs': len(d.get('images') or []),
        'specs': len(d.get('specs') or []),
        'serviceLabels': d.get('serviceLabels', []),
        'isFreeSample': pf.get('isFreeSample'),
        'isCrossBorder': pf.get('isCrossBorder'),
        'skuImages': len(d.get('skuImages') or []),
        'qtyPrices': len(d.get('quantityPrices') or d.get('priceRanges') or []),
        'posRate': st.get('positiveReviewRate'),
        'repeatRate': st.get('repeatRate'),
        'repeatBuyers': st.get('repeatBuyers'),
        'crossBuyers': st.get('crossBorderBuyers'),
        'respRate': st.get('responseRate'),
        'totalOffers': st.get('totalOffers'),
        'fTags': [(t.get('text'), t.get('value')) for t in (s.get('factoryTags') or [])],
        'cert': (s.get('certification') or {}).get('type'),
        'rank': (s.get('rank') or {}).get('text'),
        'originM': bool(s.get('originMerchant')),
        'rawCard_n': len(st.get('rawCardDetail') or []),
    }

names = list(prods.keys())

def row(label, key, fmt='str'):
    out = f'{label:20s} | '
    for n in names:
        v = prods[n][key]
        if isinstance(v, list):
            s = str(len(v)) + '项' if v else '-'
        elif isinstance(v, bool):
            s = 'Y' if v else '-'
        elif v is None or v == '' or v == 0:
            s = '-'
        else:
            s = str(v)[:13]
        out += f'{s:13s} | '
    return out

print('=' * 100)
print('表1: 100% 必返 (6个产品全部有值)')
print('=' * 100)
hdr = f'{"字段":20s} | ' + ' | '.join(f'{n[:11]:13s}' for n in names)
print(hdr)
print('-' * 100)
for label, key in [
    ('title','title'), ('price_min','price_min'), ('moq','moq'), ('sold','sold'),
    ('unit','unit'), ('imgs','imgs'), ('specs','specs'), ('serviceLabels','serviceLabels'),
    ('isFreeSample','isFreeSample'), ('isCrossBorder','isCrossBorder'),
    ('shop_years','shop_years'), ('fans','fans'), ('legalName','legalName'),
    ('title','title'), ('skuImages','skuImages'), ('qtyPrices','qtyPrices'),
]:
    print(row(label, key))

print()
print('=' * 100)
print('表2: 等级判别 flags')
print('=' * 100)
print(hdr)
print('-' * 100)
for label, key in [('isYuantouFlagship','yt'), ('isSuperFactory','sf'), ('isFactory','fac'), ('founded','founded')]:
    print(row(label, key))

print()
print('=' * 100)
print('表3: 条件返回 — 店铺信誉数据 (核心差异)')
print('=' * 100)
print(hdr)
print('-' * 100)
for label, key in [
    ('好评率(posRate)','posRate'), ('回头率(repeatRate)','repeatRate'),
    ('复购买家','repeatBuyers'), ('跨境买家','crossBuyers'),
    ('响应率','respRate'), ('factoryTags','fTags'),
    ('认证(cert)','cert'), ('排名(rank)','rank'),
    ('originMerchant','originM'), ('总商品数','totalOffers'),
]:
    print(row(label, key))

# Also print the rawCardDetail info
print()
print('=' * 100)
print('表4: rawCardDetail 内容对比')
print('=' * 100)
for n in names:
    p = prods[n]
    rc = p['rawCard_n']
    pr = p['posRate']
    ft = p['fTags']
    print(f'{n:20s} | rawCard={rc} | posRate={pr} | factoryTags={ft}')
