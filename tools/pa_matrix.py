#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全藥「事前審查 × 癌別」交叉盤點（坑 #56）。

判準＝**使用者實際看到什麼**：對每支藥的每個癌別，模擬渲染器的篩選邏輯，
再看篩出來的條文裡有沒有事審字樣。

背景：事審是「條文層」的要求，不是「藥品層」的屬性。同一支藥在不同癌別的
事審條件可能不同 —— 曾因此讓肺癌病人的 TS-1 被醫院系統擋住。

用法：python3 tools/pa_matrix.py [index.html]
"""
import re, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_drugs as L

PA = re.compile(r"事前審查")


def tag_hit(tags, sel):
    if not tags or "*" in tags:
        return True
    return any(t in sel for t in tags)


def pa_clauses(d, sel):
    """模擬渲染後，該癌別下看得到的條文中帶事審者的位置（sel=None 表示不篩選）"""
    filtering = bool(sel)
    where = []
    for it in d.get("items", []):
        if filtering and not tag_hit(it.get("cancerTags"), sel):
            continue
        if PA.search(it.get("header") or ""):
            where.append(f"第 {it['num']} 項")
        subs = it.get("subitems", [])
        if filtering and any(s.get("cancerTags") for s in subs):
            subs = [s for s in subs if tag_hit(s.get("cancerTags"), sel)]
        for s in subs:
            if PA.search(s.get("text") or ""):
                where.append(f"第 {it['num']} 項 {s['num']}")
    return where


def run(ship):
    drugs = L.load_drugs(ship)
    buckets, detail = defaultdict(list), []

    for d in drugs:
        if d.get("deleted"):
            buckets["已刪除"].append(d["num"]); continue
        cs = d.get("cancers") or []
        if not cs:
            buckets["無癌別"].append(d["num"]); continue
        per = {c: pa_clauses(d, [c]) for c in cs}
        need = [c for c in cs if per[c]]
        free = [c for c in cs if not per[c]]
        has_form = bool(d.get("form_no"))
        if need and free:
            kind = "★分歧"
        elif need:
            kind = "全癌別皆需"
        elif has_form:
            kind = "僅附表推定"
        else:
            kind = "皆不需"
        buckets[kind].append(d["num"])
        detail.append(dict(num=d["num"], name=d["name"], kind=kind, cancers=cs,
                           need=need, free=free, form=d.get("form_no") or "",
                           per=per, all_pa=pa_clauses(d, None)))

    order = ["★分歧", "全癌別皆需", "僅附表推定", "皆不需", "已刪除", "無癌別"]
    with open("report_pa_matrix.txt", "w", encoding="utf-8") as f:
        f.write("全藥「事前審查 × 癌別」交叉盤點\n")
        f.write(f"出版檔：{ship}｜藥品 {len(drugs)}\n")
        f.write("判準＝模擬渲染後、使用者在該癌別下實際看得到的條文是否含「事前審查」\n\n")
        f.write("=== 分類統計 ===\n")
        for k in order:
            if buckets[k]:
                f.write(f"{k:14s} {len(buckets[k]):3d}  {', '.join(buckets[k][:16])}"
                        f"{' …' if len(buckets[k]) > 16 else ''}\n")
        f.write("\n\n===== ★分歧：同藥不同癌，有些要事審有些不要 =====\n")
        for x in [y for y in detail if y["kind"] == "★分歧"]:
            f.write(f"\n【{x['num']}】{x['name']}{'  附表=' + x['form'] if x['form'] else ''}\n")
            f.write(f"   需事審：{x['need']}\n   不需要：{x['free']}\n")
            for c in x["cancers"]:
                w = x["per"][c]
                f.write(f"     · {c:8s} {'需事審' if w else '不需  '}  {('位置 ' + '、'.join(w)) if w else ''}\n")
        f.write("\n\n===== 僅附表推定（條文無事審字樣，訊號來自附表編號）=====\n")
        for x in [y for y in detail if y["kind"] == "僅附表推定"]:
            f.write(f"{x['num']:9s}{x['name'][:26]:28s}附表 {x['form']:12s}{x['cancers']}\n")
        f.write("\n\n===== 全癌別皆需事審 =====\n")
        for x in [y for y in detail if y["kind"] == "全癌別皆需"]:
            f.write(f"{x['num']:9s}{x['name'][:26]:28s}{x['cancers']}\n")

    print(f"藥品 {len(drugs)}")
    for k in order:
        if buckets[k]:
            print(f"  {k:14s} {len(buckets[k]):3d}")
    print("\n★分歧清單：")
    for x in [y for y in detail if y["kind"] == "★分歧"]:
        print(f"  {x['num']:9s}{x['name'][:24]:26s}需={x['need']} 不需={x['free']}")
    print("\n-> report_pa_matrix.txt")
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else "index.html"))
