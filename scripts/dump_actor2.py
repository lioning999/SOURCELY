"""临时脚本：用指定 Apify actor 抓取 1688 商品 → web/temp/"""
import asyncio, json, os, sys
from datetime import timedelta
from apify_client import ApifyClientAsync

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'api'))
from config import Config

ACTOR_ID = "ghXSMZcW3GxsCrkiR"
URL = "https://detail.1688.com/offer/685469710262.html"
OFFER_ID = "685469710262"
OUT = os.path.join(os.path.dirname(__file__), '..', 'src', 'web', 'temp', f'{OFFER_ID}_actor2.json')

async def main():
    for i, token in enumerate(Config.APIFY_TOKENS, 1):
        if not token:
            continue
        client = ApifyClientAsync(token=token)
        try:
            print(f"Token {i}: calling actor {ACTOR_ID}...")
            run = await client.actor(ACTOR_ID).call(
                run_input={"startUrls": [URL], "offerIds": [OFFER_ID]},
                wait_duration=timedelta(seconds=Config.APIFY_WAIT_SECONDS),
            )
            if run is None:
                print(f"Token {i}: run returned None")
                continue

            page = await client.dataset(run.default_dataset_id).list_items(limit=5)
            items = page.items
            if not items:
                print(f"Token {i}: dataset empty")
                continue

            if len(items) == 1 and items[0].get("limit_reached"):
                print(f"Token {i}: quota exhausted, switching...")
                continue

            with open(OUT, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
            size = os.path.getsize(OUT)
            print(f"Done → {OUT}  ({size} bytes, {len(items)} items)")
            return
        except Exception as e:
            print(f"Token {i}: error - {e}")
            continue
    print("All tokens failed")

asyncio.run(main())
