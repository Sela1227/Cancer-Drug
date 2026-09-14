#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
機械式全文差異回歸（坑 #51）。雙向比對，兩個方向問的是不同問題：
  正向：原文每句是否都在出版檔 -> 漏抄 / 漏段
  反向：出版檔每句是否都在原文 -> 錯字 / 幻覺 / 重複

價值不在第一次跑出多少筆，而在能不能把誤報壓到 0 ——
壓到 0 之後，任何一筆新出現的差異都是真的。

用法：python3 tools/diff_source.py [index.html] [chap9_xxx.pdf]
"""
import re, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_drugs as L

MINLEN = 12
NUMBERING = re.compile(
    r"^(?:[0-9０-９]{1,3}|[（(][0-9０-９]{1,3}[)）]|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]|[IVXivx]{1,4}|[ⅰⅱⅲⅳⅴ])[.、)）]?$")
DATEONLY = re.compile(r"^[（(]?[0-9０-９/、\s]+[)）]?$")
LEADSTRIP = [
    re.compile(r"^[（(][0-9０-９/、\s]+[)）]\s*"),
    re.compile(r"^(?:[0-9０-９]{1,3}[.、]|[（(][0-9０-９]{1,3}[)）]|[ⅠⅡⅢⅣⅤ][.、]"
               r"|[IVX]{1,4}[.、]|[ⅰⅱⅲⅳⅴ][.、]|[ivx]{1,4}[.、])\s*"),
]


def sentences(text):
    out = []
    for chunk in re.split(r"[。；;\n]", text or ""):
        c = chunk.strip()
        if not c:
            continue
        for _ in range(4):          # 句首可能連續出現日期括號與條號
            c2 = c
            for rx in LEADSTRIP:
                c2 = rx.sub("", c2)
            if c2 == c:
                break
            c = c2
        if not c or DATEONLY.match(c) or NUMBERING.match(c):
            continue
        out.append(c)
    return out


def header_info(d):
    """藥品標題行的可解釋內容（存成 name/brand/form_no/revisions，不在條文裡）"""
    return L.norm((d.get("num") or "") + (d.get("name") or "") + (d.get("brand") or "") +
                  (d.get("form_no") or "") + "".join(d.get("revisions") or []))


def strip_title(seg):
    """剝掉藥品標題行 —— 標題可能跨行，讀到第一個「：」為止"""
    lines = seg.split("\n")
    cut = 0
    for i, ln in enumerate(lines[:4]):
        cut = i + 1
        if "：" in ln or ":" in ln:
            break
    return "\n".join(lines[cut:])


def run(ship, src):
    drugs = L.load_drugs(ship)
    D = {d["num"]: d for d in drugs}
    SEC = L.split_sections(L.read_source(src))

    # 父項目的 items 是子藥物的合併複本，逐節必然對不上 -> 用全庫底本兜底
    G_SHIP = L.norm("\n".join(L.drug_text(d) for d in drugs) +
                    "\n".join(header_info(d) for d in drugs))
    G_SRC = L.norm("\n".join(SEC.values()))

    miss, extra, nosec = [], [], []
    only_global = {"miss": 0, "extra": 0}

    for num, seg in SEC.items():
        d = D.get(num)
        if not d:
            nosec.append(num)
            continue
        ship_flat = L.norm(L.drug_text(d))
        hdr = header_info(d)

        for sent in sentences(strip_title(seg)):          # 正向
            k = L.norm(sent)
            if len(k) < MINLEN or k in ship_flat or k in hdr:
                continue
            if k in G_SHIP:
                only_global["miss"] += 1
                continue
            miss.append((num, sent[:100]))

        if d.get("deleted"):     # 已刪除條號的說明文字是我們寫的，不做反向
            continue
        src_flat = L.norm(seg)
        for sent in sentences(L.drug_text(d)):            # 反向
            k = L.norm(sent)
            if len(k) < MINLEN or k in src_flat:
                continue
            if k in G_SRC:
                only_global["extra"] += 1
                continue
            extra.append((num, sent[:100]))

    with open("report_fulldiff.txt", "w", encoding="utf-8") as f:
        f.write("機械式全文差異回歸\n")
        f.write(f"來源：{src}\n出版檔：{ship}\n")
        f.write(f"官方條號 {len(SEC)}｜出版檔藥品 {len(drugs)}｜句長門檻 {MINLEN}\n")
        f.write(f"逐節對不上但全庫底本有（父/子合併的歸屬差異，非遺失）："
                f"正向 {only_global['miss']}、反向 {only_global['extra']}\n\n")
        f.write(f"===== 原文有、出版檔沒有（疑漏抄）：{len(miss)} =====\n")
        for x in miss:
            f.write(f"{x[0]:9s} | {x[1]}\n")
        f.write(f"\n===== 出版檔有、原文沒有（疑錯字／幻覺）：{len(extra)} =====\n")
        for x in extra:
            f.write(f"{x[0]:9s} | {x[1]}\n")
        f.write(f"\n===== 官方有條號但出版檔沒有：{len(nosec)} =====\n")
        for x in nosec:
            f.write(f"{x}\n")
        if miss or extra:
            f.write("\n=== 涉及藥品統計 ===\n")
            for k, v in Counter([x[0] for x in miss + extra]).most_common():
                f.write(f"{k:9s} {v}\n")

    print(f"漏抄 {len(miss)}｜疑錯字 {len(extra)}｜未收錄條號 {len(nosec)}"
          f"（歸屬差異已扣除：正向 {only_global['miss']}、反向 {only_global['extra']}）"
          f" -> report_fulldiff.txt")
    for x in miss[:6]:
        print("  漏:", x[0], x[1][:56])
    for x in extra[:6]:
        print("  多:", x[0], x[1][:56])
    return 1 if (miss or extra or nosec) else 0


if __name__ == "__main__":
    sys.exit(run(*L.resolve_args(sys.argv)))
