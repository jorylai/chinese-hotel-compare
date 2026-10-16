#!/usr/bin/env python3
"""TripGenie 查询（Trip.com 官方 skill API）

TripGenie 是 Trip.com Group 官方的 AI travel skill，提供实时价格、详情、预订链接。
国内版对应的是 TripAI（携程问道）。

认证：TRIPGENIE_API_KEY 环境变量
  Key 去 https://www.trip.com/tripgenie/openclaw 申请
接口：POST https://tripgenie-openclaw-prod.trip.com/openclaw/query
  body: {"token": "<key>", "query": "<自然语言问句>"}

用法：
  export TRIPGENIE_API_KEY=<key>
  python3 tripgenie-query.py --query "德清莫干山皇冠假日酒店10月17日入住10月18日离店价格"
"""
import argparse
import json
import os
import sys
import urllib.request

ENDPOINT = "https://tripgenie-openclaw-prod.trip.com/openclaw/query"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True, help="自然语言查询")
    ap.add_argument("--raw", action="store_true", help="输出原始响应")
    args = ap.parse_args()

    api_key = os.environ.get("TRIPGENIE_API_KEY")
    if not api_key:
        print("error: 未设置 TRIPGENIE_API_KEY 环境变量", file=sys.stderr)
        print("去 https://www.trip.com/tripgenie/openclaw 申请 Key", file=sys.stderr)
        raise SystemExit(1)

    payload = json.dumps({"token": api_key, "query": args.query}).encode()
    req = urllib.request.Request(
        ENDPOINT, data=payload, method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"error: HTTP {e.code}: {e.read().decode()[:500]}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1)

    # 尝试解析为 JSON，失败则直接输出原文（可能是 Markdown）
    try:
        data = json.loads(text)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(text)


if __name__ == "__main__":
    main()
