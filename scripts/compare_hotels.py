#!/usr/bin/env python3
"""多平台酒店比价工具

平台：
  - 飞猪：flyai CLI（@fly-ai/flyai-cli；体验模式价格打码如 ¥2xx，
    正式 API Key 去 https://flyai.open.fliggy.com/ 申请后
    `flyai config set FLYAI_API_KEY <key>`）
  - 美团：ht-ai CLI（@meituan-travel/ht-ai；需 MEITUAN_HT_TOKEN 环境变量，
    或 ~/.config/meituan-travel/config.json；token 去美团开放平台申请）
  - 携程：问道官方 skill 接口 wendao-skill-prod.ctrip.com/skill/query
    （匿名可用，无需 token；价格为区间口径）

用法：
  export MEITUAN_HT_TOKEN=<token>   # 美团（可选，不配则美团侧报错跳过）
  python3 scripts/compare_hotels.py --city 杭州 --check-in 2026-11-20 --check-out 2026-11-21
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "node_modules", ".bin")


def which_cli(name):
    """优先用项目本地 node_modules/.bin，其次用 PATH 上的全局安装"""
    local = os.path.join(BIN, name)
    if os.path.exists(local):
        return local
    return shutil.which(name)


def run(cmd, timeout=90, env=None):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, env=env)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError as e:
        return -1, "", str(e)


def search_feizhu(city, check_in, check_out, limit=10):
    """飞猪 flyai"""
    cli = which_cli("flyai")
    if not cli:
        return {"platform": "飞猪", "ok": False,
                "error": "未找到 flyai CLI，先 npm install"}
    cmd = [cli, "search-hotel",
           "--dest-name", city,
           "--check-in-date", check_in, "--check-out-date", check_out]
    rc, out, err = run(cmd, timeout=120)
    if rc != 0:
        return {"platform": "飞猪", "ok": False, "error": err or out or f"exit {rc}"}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"platform": "飞猪", "ok": False, "error": "返回非 JSON"}
    items = (data.get("data") or {}).get("itemList") or []
    hotels = []
    for it in items[:limit]:
        hotels.append({
            "name": it.get("name"),
            "price": it.get("price"),
            "star": it.get("star"),
            "address": it.get("address"),
            "url": it.get("detailUrl"),
        })
    note = None
    if data.get("systemMessage"):
        note = "体验模式：价格打码，正式 Key 去 flyai.open.fliggy.com 申请"
    return {"platform": "飞猪", "ok": True, "hotels": hotels, "note": note}


def search_meituan(city, check_in, check_out, limit=10):
    """美团 ht-ai CLI（官方，需 MEITUAN_HT_TOKEN）"""
    cli = which_cli("ht-ai")
    if not cli:
        return {"platform": "美团", "ok": False,
                "error": "未找到 ht-ai CLI，先 npm install"}
    if not os.environ.get("MEITUAN_HT_TOKEN"):
        # ht-ai 也支持 ~/.config/meituan-travel/config.json，这里只做提示
        print("  ℹ️ 未检测到 MEITUAN_HT_TOKEN，ht-ai 将尝试读本地 config.json",
              file=sys.stderr)
    query = f"{city}{check_in}入住{check_out}离店的酒店推荐"
    cmd = [cli, "query", "--query", query,
           "--city", city, "--origin-query", query, "-o", "json"]
    rc, out, err = run(cmd, timeout=150)
    if rc != 0:
        return {"platform": "美团", "ok": False, "error": err or out or f"exit {rc}"}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        # ht-ai 默认输出可能是纯文本，尝试直接解析文本
        hotels = parse_meituan_markdown(out, limit)
        return {"platform": "美团", "ok": True, "hotels": hotels,
                "note": "自然语言接口，价格为'￥xxx起/晚'口径"}
    text = data.get("data") if isinstance(data, dict) else str(data)
    hotels = parse_meituan_markdown(text or "", limit)
    return {"platform": "美团", "ok": True, "hotels": hotels,
            "note": "自然语言接口，价格为'￥xxx起/晚'口径"}


def parse_meituan_markdown(text, limit):
    """从美团返回的 Markdown 里抽酒店名和价格"""
    import re
    hotels = []
    # 形如 [**如家酒店·neo\(杭州...店\)**](url) ... ￥273起/晚
    for m in re.finditer(
            r"\[\*\*(.+?)\*\*\]\(http[^)]+\)[^\n]*?￥([0-9Xx]+)(起)?/晚", text):
        name = m.group(1).replace("\\", "")
        price = f"￥{m.group(2)}/晚"
        hotels.append({"name": name, "price": price, "star": "",
                       "address": "", "url": ""})
        if len(hotels) >= limit:
            break
    return hotels


def search_xiecheng(city, check_in, check_out, limit=10):
    """携程问道官方 skill 接口（匿名可用，无需 token）

    POST https://wendao-skill-prod.ctrip.com/skill/query
    body: {"query": "<自然语言问句>"}
    """
    import urllib.request
    query = (f"{city}酒店，{check_in}入住，{check_out}离店，1间房，"
             f"请推荐并给出每家酒店的价格区间")
    payload = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        "https://wendao-skill-prod.ctrip.com/skill/query",
        data=payload, method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001 - 网络失败直接记为平台不可用
        return {"platform": "携程", "ok": False, "error": f"请求失败: {e}"}
    hotels = parse_xiecheng_markdown(text, limit)
    return {"platform": "携程", "ok": True, "hotels": hotels,
            "note": "携程问道官方接口（匿名）；价格为区间口径，非实时可订价"}


def parse_xiecheng_markdown(text, limit):
    """从携程问道返回的 Markdown 里抽酒店名、价格和预订链接。

    返回格式不固定（LLM 生成），兼容：
      - 酒店名：### <如家酒店neo(…店）> / ### 杭州中山西子湖酒店
      - 价格：200-350元 / 539元起/晚 / 539元/晚
      - 链接：[预定链接](<https://m.ctrip.com/…>)
    """
    import re
    hotels = []
    hotel_kw = re.compile(r"酒店|民宿|客栈|公寓|旅店|宾馆|度假村|青旅|hostel|hotel", re.I)
    # 按 ### 标题切块
    blocks = re.split(r"^###\s*", text, flags=re.M)
    for blk in blocks[1:]:
        first_line = blk.split("\n", 1)[0].strip().strip("<>")
        if not first_line or not hotel_kw.search(first_line):
            continue
        name = first_line
        price = "价格见原文"
        pm = re.search(r"(?:约)?(\d+)\s*[-~～]\s*(\d+)\s*元", blk)
        if pm:
            price = f"￥{pm.group(1)}-{pm.group(2)}/晚"
        else:
            pm = re.search(r"(\d+)\s*元起/晚", blk)
            if pm:
                price = f"￥{pm.group(1)}起/晚"
            else:
                pm = re.search(r"(\d+)\s*元/晚", blk)
                if pm:
                    price = f"￥{pm.group(1)}/晚"
                else:
                    pm = re.search(r"(\d+)\s*元起", blk)
                    if pm:
                        price = f"￥{pm.group(1)}起"
        um = re.search(r"\[预定链接\]\(\s*<([^>]+)>", blk)
        url = um.group(1) if um else ""
        hotels.append({"name": name, "price": price, "star": "",
                       "address": "", "url": url})
        if len(hotels) >= limit:
            break
    return hotels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True, help="城市，如 杭州")
    ap.add_argument("--check-in", required=True)
    ap.add_argument("--check-out", required=True)
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--out", default="", help="结果 JSON 保存路径")
    args = ap.parse_args()

    results = [
        search_feizhu(args.city, args.check_in, args.check_out, args.limit),
        search_meituan(args.city, args.check_in, args.check_out, args.limit),
        search_xiecheng(args.city, args.check_in, args.check_out),
    ]

    # 控制台表格
    print(f"\n# {args.city} {args.check_in} → {args.check_out} 酒店比价\n")
    for r in results:
        print(f"## {r['platform']}")
        if not r["ok"]:
            print(f"  ⚠️ {r['error']}\n")
            continue
        if r.get("note"):
            print(f"  ℹ️ {r['note']}")
        for h in r.get("hotels", []):
            print(f"  - {h['name']}｜{h['price']}｜{h['star'] or '-'}｜{h['address'] or ''}")
        print()

    out_path = args.out or os.path.join(
        ROOT, "results", f"{args.city}-{args.check_in}-{args.check_out}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    payload = {"city": args.city, "check_in": args.check_in,
               "check_out": args.check_out,
               "compared_at": datetime.now().isoformat(timespec="seconds"),
               "results": results}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"结果已保存: {out_path}")


if __name__ == "__main__":
    main()
