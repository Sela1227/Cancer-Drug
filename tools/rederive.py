#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
出版檔的 cancerTags 必須等於規則重推的結果（坑 #53）。

防的是：為了修別的問題直接編輯出版檔、繞過推導規則，
造成標籤與規則靜默脫鉤 —— 資料看起來一樣，但「為什麼是這個值」的答案不見了。

用法：
  python3 tools/rederive.py [index.html]            # 只比對，不寫檔
  python3 tools/rederive.py [index.html] --write    # 一致時寫回稽核檔
"""
import json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_drugs as L
import derive_tags as T

AUDIT_KEYS = ("cancerTagSource", "cancerTagRule")


def run(ship, write=False):
    drugs = L.load_drugs(ship)
    diffs, n_item, n_sub = [], 0, 0

    for d in drugs:
        if d.get("deleted"):        # 已刪除條號的說明文字是我們寫的
            for it in d.get("items", []):
                it.setdefault("cancerTags", ["*"])
                it["cancerTagSource"], it["cancerTagRule"] = "deleted-notice", []
            continue
        want = T.derive_for_drug(d, L.is_marker)
        for ii, it in enumerate(d.get("items", [])):
            w, src, rule = want[(ii, None)]
            if it.get("cancerTags") != w:
                diffs.append((d["num"], f"item {it['num']}", it.get("cancerTags"), w, src))
            it["cancerTagSource"], it["cancerTagRule"] = src, rule
            n_item += 1
            for si, s in enumerate(it.get("subitems", [])):
                w2, s2, r2 = want[(ii, si)]
                if (s.get("cancerTags") or ["*"]) != w2:
                    diffs.append((d["num"], f"{it['num']}/{s['num']}",
                                  s.get("cancerTags"), w2, s2))
                s["cancerTagSource"], s["cancerTagRule"] = s2, r2
                n_sub += 1

    cnt = Counter()
    for d in drugs:
        for it in d.get("items", []):
            cnt[it.get("cancerTagSource", "?")] += 1
            for s in it.get("subitems", []):
                cnt["sub:" + s.get("cancerTagSource", "?")] += 1

    with open("report_rederive.txt", "w", encoding="utf-8") as f:
        f.write(f"出版檔：{ship}\n比對節點：item {n_item}、subitem {n_sub}\n")
        f.write(f"\n=== 出版檔標籤 vs 規則重推 不一致：{len(diffs)} ===\n")
        for x in diffs:
            f.write(f"{x[0]:9s} {x[1]:<16s} 出版={x[2]} 規則={x[3]} ({x[4]})\n")
        f.write("\n=== 推導來源統計 ===\n")
        for k in sorted(cnt):
            f.write(f"{k:36s} {cnt[k]}\n")

    print(f"比對 {n_item} item / {n_sub} subitem｜不一致 {len(diffs)} -> report_rederive.txt")
    for x in diffs[:12]:
        print("  ", x[0], x[1], "出版", x[2], "規則", x[3])

    if write:
        if diffs:
            print("→ 有不一致，未寫出（先解決差異再寫）")
        else:
            json.dump(drugs, open("drugs_audit.json", "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            print("→ 已寫出 drugs_audit.json（含溯源欄位）")
    return 1 if diffs else 0


if __name__ == "__main__":
    ship = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "index.html"
    sys.exit(run(ship, "--write" in sys.argv))
