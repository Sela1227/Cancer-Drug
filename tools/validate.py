#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
建置端合規閘門。分兩級：
  BLOCK — 任何一筆就不得出版（exit 1）
  WARN  — 只產報告，不阻止出版

為什麼放建置端而不是 runtime：瀏覽器丟例外會讓個管師看到空白頁（坑 #40）。

用法：python3 tools/validate.py [index.html] [chap9_xxx.pdf]
"""
import json, re, subprocess, sys, unicodedata
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib_drugs as L
import derive_tags as T

block, warn = [], []


def main(ship, src):
    drugs = L.load_drugs(ship)
    D = {d["num"]: d for d in drugs}
    raw = L.read_source(src)
    SEC = L.split_sections(raw)
    flat_src = L.flat(raw)
    lower_src = flat_src.lower()

    def nodes(d):
        for it in d.get("items", []):
            yield f"item {it['num']}", it, it.get("header") or ""
            for s in it.get("subitems", []):
                yield f"  {it['num']}/{s['num']}", s, s.get("text") or ""

    # ---- BLOCK 1：文字截斷 / 括號不平衡 ----
    TRUNC = re.compile(r"[、（(／/]\s*$|(?:及|與)\s*$")
    for d in drugs:
        for lab, n, t in nodes(d):
            if t and TRUNC.search(t.strip()):
                block.append(("截斷條文", d["num"], lab, t.strip()[-30:]))
            if t.count("(") + t.count("（") != t.count(")") + t.count("）"):
                block.append(("括號不平衡", d["num"], lab, t.strip()[:40]))

    # ---- BLOCK 2：數值單位損失（含空白變體）----
    UNIT_BAD = [
        (re.compile(r"mg\s*/\s*m(?![²0-9a-zA-Z])"), "mg/m 缺上標"),
        (re.compile(r"1\.73\s*m(?![²0-9])"), "1.73m 缺上標"),
        (re.compile(r"/\s*mm(?![³²0-9Hh])"), "/mm 缺上標"),
        (re.compile(r"/\s*mm\s*[23](?![\d])"), "mm2/mm3 未轉 Unicode"),
        (re.compile(r"mg/m2\b"), "mg/m2 未轉 Unicode"),
        (re.compile(r"10\s*[-^]\s*(?![0-9⁻])"), "10 指數缺數字"),
        (re.compile(r"[×x]\s*10(?![\d⁰-⁹])"), "×10 缺指數"),
    ]
    for d in drugs:
        for lab, n, t in nodes(d):
            for rx, msg in UNIT_BAD:
                if rx.search(t or ""):
                    block.append((msg, d["num"], lab, (t or "")[:50]))

    # ---- BLOCK 3：標籤合法性 ----
    for d in drugs:
        for lab, n, t in nodes(d):
            tags = n.get("cancerTags")
            if not tags:
                block.append(("cancerTags 缺失或空", d["num"], lab, "")); continue
            if "*" in tags and len(tags) > 1:
                block.append(('"*" 不可與癌別並存', d["num"], lab, str(tags)))
            for x in tags:
                if x != "*" and x not in T.CANCERS:
                    block.append(("未知癌別", d["num"], lab, x))

    # ---- BLOCK 4：藥物層 cancers = 標籤聯集 ----
    for d in drugs:
        want = T.cancers_from_tags(d)
        if want:
            if set(d.get("cancers") or []) != set(want):
                block.append(("cancers 不等於條文標籤聯集", d["num"], "",
                              f"{d.get('cancers')} vs {want}"))
        elif not d.get("cancers") and not d.get("deleted"):
            block.append(("cancers 為空", d["num"], "", "全條文皆 * 且無人工分類"))

    # ---- BLOCK 5：父子同條文標籤一致 ----
    for d in drugs:
        kids = [D[k] for k in D if k.startswith(d["num"] + ".")]
        if not kids:
            continue
        ktags = defaultdict(set)
        for k in kids:
            for lab, n, t in nodes(k):
                ktags[L.norm(t)].add(tuple(n.get("cancerTags") or []))
        for lab, n, t in nodes(d):
            h = L.norm(t)
            if h and h in ktags and tuple(n.get("cancerTags") or []) not in ktags[h]:
                block.append(("父子同條文標籤不一致", d["num"], lab,
                              f"父 {n.get('cancerTags')} vs 子 {sorted(ktags[h])}"))

    # ---- BLOCK 6：事前審查父子一致 ----
    for d in drugs:
        kids = [D[k] for k in D if k.startswith(d["num"] + ".")]
        own = ("事前審查" in L.flat(L.drug_text(d))) or bool(d.get("form_no"))
        if kids:
            kpa = [("事前審查" in L.flat(L.drug_text(k))) or bool(k.get("form_no")) for k in kids]
            expect = own or any(kpa)
            scope = "all" if (own or all(kpa)) else ("partial" if any(kpa) else "none")
        else:
            expect, scope = own, ("all" if own else "none")
        if bool(d.get("pre_review")) != expect:
            block.append(("pre_review 不等於 自身 OR 子項", d["num"], "",
                          f"{d.get('pre_review')} vs {expect}"))
        if d.get("review_scope") != scope:
            block.append(("review_scope 推導不符", d["num"], "",
                          f"{d.get('review_scope')} vs {scope}"))

    # ---- BLOCK 7：藥名 / 商品名必須逐字存在於原文（抓拼字錯誤，坑 #49）----
    for d in drugs:
        for field in ("name", "brand"):
            v = d.get(field) or ""
            for part in re.split(r"[、；;/,]", v):
                q = L.flat(part).lower()
                if len(q) >= 4 and q not in lower_src:
                    block.append(("藥名/商品名不在原文中（疑拼字錯誤）",
                                  d["num"], field, part.strip()))

    # ---- BLOCK 8：lead / revisions 必須源自原文 ----
    for d in drugs:
        ld = d.get("lead")
        if ld and L.flat(ld) not in flat_src:
            block.append(("lead 不在原文中", d["num"], "", ld[:40]))
        for rv in (d.get("revisions") or []):
            if not re.match(r"^\d{2,3}/\d{1,2}/\d{1,2}$", rv):
                block.append(("revisions 日期格式異常", d["num"], "", rv))

    # ---- BLOCK 9：官方條號必須全數收錄（含「（刪除）」）----
    for n in SEC:
        if n not in D:
            block.append(("官方條號未收錄", n, "", "違反完整收錄政策"))

    # ---- BLOCK 10：無編號前導句不可佔用 item 1（條號需對齊官方）----
    for d in drugs:
        seg = SEC.get(d["num"])
        items = d.get("items") or []
        if not seg or not items or L.is_marker(items[0]):
            continue
        key = L.flat(items[0].get("header") or "")[:22]
        if len(key) < 10:
            continue
        fseg = L.flat(seg)
        p = fseg.find(key)
        if p <= 0:
            continue
        lead_type = bool(re.search(r"[)）：:]$", fseg[max(0, p - 3):p]))
        has_official_1 = bool(re.search(r"[)）。：:]1\.", fseg))
        if lead_type and has_official_1 and len(items) >= 2:
            block.append(("無編號前導句佔用 item 1（條號位移）", d["num"], "",
                          (items[0].get("header") or "")[:40]))

    # ---- BLOCK 11：結構化表格 ----
    for d in drugs:
        for it in d.get("items", []):
            for sb in it.get("subitems", []):
                tb = sb.get("table")
                if not tb:
                    continue
                ncol = len(tb["columns"])
                if ncol < 2:
                    block.append(("表格欄位數異常", d["num"], sb["num"], str(ncol)))
                for r in tb["rows"]:
                    if len(r["cells"]) != ncol:
                        block.append(("表格列格數不符欄數", d["num"],
                                      f"{sb['num']} {r['code']}",
                                      f"{len(r['cells'])} vs {ncol}"))
                    if not r.get("cancerTags"):
                        block.append(("表格列缺 cancerTags", d["num"],
                                      f"{sb['num']} {r['code']}", ""))

    # ---- BLOCK 12/13：委派給兩支獨立腳本 ----
    for scr, pat, name in ((HERE / "diff_source.py",
                            r"漏抄 (\d+)｜疑錯字 (\d+)｜未收錄條號 (\d+)", "全文差異回歸"),
                           (HERE / "rederive.py", r"不一致 (\d+)", "標籤規則重推")):
        try:
            args = [sys.executable, str(scr), ship] + ([src] if "diff" in scr.name else [])
            r = subprocess.run(args, capture_output=True, text=True, timeout=600)
            out = (r.stdout or "").strip().splitlines()
            m = re.search(pat, out[0] if out else "")
            if not m:
                block.append((f"{name}無法解析結果", "", "", (out[0] if out else "")[:80]))
            elif any(int(g) for g in m.groups()):
                block.append((f"{name}未通過", "", "", m.group(0)))
        except Exception as e:
            block.append((f"{name}執行失敗", "", "", str(e)[:80]))

    # ---- WARN ----
    VAGUE = {"卵巢", "輸卵管", "子宮頸", "睪丸", "唾液腺", "胸腺", "漿細胞", "頭頸部"}
    for d in drugs:
        for lab, n, t in nodes(d):
            tags = n.get("cancerTags") or []
            src_k = n.get("cancerTagSource")
            rule = n.get("cancerTagRule") or []
            if tags == ["*"] and src_k not in ("inherit-parent-indication", "deleted-notice"):
                cs, hits = T.scan_diseases(t)
                if cs:
                    warn.append(("含癌名卻判為 *（多為行政條文，需確認）", d["num"], lab,
                                 f"{sorted(cs)} {hits[:3]}"))
            if len([x for x in tags if x != "*"]) >= 3:
                warn.append(("單一條文命中 3+ 癌別", d["num"], lab, str(tags)))
            if src_k == "text-rule" and len(rule) == 1 and any(v in rule[0] for v in VAGUE):
                warn.append(("僅靠單一模糊器官詞命中", d["num"], lab, f"{rule} -> {tags}"))
            if src_k == "fallback-unclassified":
                warn.append(("fallback-unclassified（未分類，保守顯示）", d["num"], lab, ""))

    # ---- 輸出 ----
    with open("report_validate.txt", "w", encoding="utf-8") as f:
        f.write(f"出版檔：{ship}\n原文：{src}\n\n")
        f.write(f"===== BLOCK（阻止出版）：{len(block)} =====\n")
        for x in block:
            f.write(" | ".join(str(y) for y in x) + "\n")
        agg = defaultdict(int)
        for x in warn:
            agg[x[0]] += 1
        f.write(f"\n===== WARN（僅警告）：{len(warn)} =====\n")
        for k in sorted(agg):
            f.write(f"  {k}: {agg[k]}\n")
        f.write("\n")
        # fallback 逐筆列會有兩百多行沒人看 -> 收成每藥計數（報告不能變噪音）
        fb = [x for x in warn if x[0].startswith("fallback-unclassified")]
        if fb:
            a2 = defaultdict(int)
            for x in fb:
                a2[x[1]] += 1
            f.write(f"--- fallback-unclassified 共 {len(fb)} 筆，分布於 {len(a2)} 支藥（收成計數）---\n")
            for k in sorted(a2, key=lambda z: (-a2[z], z)):
                f.write(f"  {k:10s} {a2[k]}\n")
            f.write("\n")
        for x in warn:
            if not x[0].startswith("fallback-unclassified"):
                f.write(" | ".join(str(y) for y in x) + "\n")

    print(f"BLOCK {len(block)} / WARN {len(warn)}  -> report_validate.txt")
    for x in block[:20]:
        print("  BLOCK:", " | ".join(str(y) for y in x))
    return 1 if block else 0


if __name__ == "__main__":
    sys.exit(main(*L.resolve_args(sys.argv)))
