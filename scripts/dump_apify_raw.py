"""一次性脚本：Apify 抓取 → 全量原始 JSON 写入 web/temp/"""
import asyncio, json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'api'))

from adapters.apify_adapter import ApifyAdapter

URL = "https://detail.1688.com/offer/1053910572406.html"
OFFER_ID = "1053910572406"
OUT = os.path.join(os.path.dirname(__file__), '..', 'src', 'web', 'temp', f'{OFFER_ID}.json')

async def main():
    print(f"Fetching {URL} ...")
    adapter = ApifyAdapter()
    raw = await adapter.fetch_product_by_url(URL)
    if raw is None:
        print("ERROR: got None from Apify")
        return
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)
    size = os.path.getsize(OUT)
    print(f"Done → {OUT}  ({size} bytes)")

asyncio.run(main())
