"""
测试 Apify 1688 Wholesale Scraper 完整返回字段。

输入: 1688 商品链接（offerId=1038913113865）
输出: 完整 JSON dump + 字段结构摘要
"""

import json
import os
import sys
import io
from pathlib import Path

# 修复 Windows GBK 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apify_client import ApifyClient

# ---------- 配置 ----------
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "YOUR_APIFY_TOKEN_HERE")
ACTOR_ID = "zen-studio/1688-wholesale-scraper"
OFFER_ID = "1038913113865"

OUT_DIR = Path(__file__).resolve().parent
OUT_JSON = OUT_DIR / "apify_raw_response.json"
OUT_SUMMARY = OUT_DIR / "apify_fields_summary.txt"

# ---------- 递归获取所有 key 路径 ----------
def list_keys(obj, prefix=""):
    """递归列出所有叶子 key 路径. 返回 [(路径, 值类型, 示例值)]"""
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            results.extend(list_keys(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(obj, list) and obj:
        # 取第一个元素展开
        first = obj[0]
        if isinstance(first, dict):
            results.extend(list_keys(first, f"{prefix}[0]"))
        else:
            results.append((f"{prefix}[]", f"list[{type(first).__name__}]", str(first)[:80]))
    else:
        val_str = str(obj)[:80] if obj is not None else "null"
        results.append((prefix, type(obj).__name__, val_str))
    return results


# ---------- 主逻辑 ----------
def main():
    print(f"▶ 启动 Apify Actor: {ACTOR_ID}")
    print(f"▶ offerId: {OFFER_ID}")
    print(f"▶ 等待返回...\n")

    client = ApifyClient(APIFY_TOKEN)

    # 启动 run + 等待完成
    run = client.actor(ACTOR_ID).call(run_input={"offerIds": [OFFER_ID]})
    # call() 返回 Run Pydantic model，转 dict 取字段
    run_dict = run.model_dump()
    # 打印所有 key 找 dataset ID
    print(f"  run keys: {list(run_dict.keys())}")
    dataset_id = run_dict.get("default_dataset_id")
    print(f"  Run ID: {run_dict.get('id')}, dataset: {dataset_id}")

    # 取 dataset
    items = list(client.dataset(dataset_id).iterate_items())

    if not items:
        print("❌ 无数据返回")
        sys.exit(1)

    data = items[0]
    print(f"✅ 返回 {len(items)} 条，取第一条\n")

    # ---- 写完整 JSON ----
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📄 完整 JSON → {OUT_JSON}  ({OUT_JSON.stat().st_size:,} bytes)")

    # ---- 生成字段摘要 ----
    keys = list_keys(data)
    lines = []
    lines.append("=" * 70)
    lines.append("Apify 1688 Wholesale Scraper — 完整返回字段")
    lines.append(f"offerId: {OFFER_ID}")
    lines.append(f"共 {len(keys)} 个叶子字段")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"{'字段路径':<55} {'类型':<12} {'示例值'}")
    lines.append("-" * 70)
    for path, typ, sample in keys:
        lines.append(f"{path:<55} {typ:<12} {sample}")

    summary = "\n".join(lines)
    OUT_SUMMARY.write_text(summary, encoding="utf-8")
    print(f"📋 字段摘要 → {OUT_SUMMARY}  ({len(keys)} 个叶子字段)")
    print(summary)


if __name__ == "__main__":
    main()
