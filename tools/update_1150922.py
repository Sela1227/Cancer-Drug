#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
115/9/22 公告更新（V5.10.0）。

與上次（update_1150821.py，外科手術式 patch）不同：本次變動 12 條 + 2 支新藥，
且來源格式升級，改用 **全庫重建**：
  · 條文與條號 ← PDF 文字（parse_section）
  · 句子內容與上標 ← DOCX（無截斷、無字間空白、真上標 run）
  · PD-L1 對照表 ← DOCX 真表格（省掉坑 #41 的錨點重建）

保留不可由原文推導的既有欄位：types、form_no 的人工補正、父項目的 marker 等。
用法：python3 tools/update_1150922.py index.html
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib_drugs as L
import derive_tags as T
import parse_section as P
import merge_sources as M

PDF_TXT = "src_0922.txt"
DOCX = "/mnt/user-data/uploads/chap9_1150922.docx"
rep = []


def norm_key(s, n=18):
    return L.norm(s)[:n]


def apply_docx_text(items, paras, cursor):
    """用 DOCX 段落取代 PDF 解析出的節點文字（修截斷、字間空白，補上標）"""
    nodes = []
    for it in items:
        nodes.append((it, "header"))
        for s in it["subitems"]:
            nodes.append((s, "text"))
    texts = [n[0][n[1]] for n in nodes]
    hits, cursor = M.align(texts, paras, cursor)
    fixed = 0
    for (node, field), h in zip(nodes, hits):
        if h is None:
            continue
        cand = paras[h]
        # 只在「正規化後等價」時才替換 —— 不同內容一律不碰（不猜）
        if L.norm(cand) == L.norm(node[field]) and cand != node[field]:
            node[field] = cand
            fixed += 1
        elif L.norm(cand) != L.norm(node[field]):
            # DOCX 版可能含上標字元，正規化後仍應相等；不等代表對齊有誤 → 跳過
            pass
    return fixed, cursor


# 官方在這些位置沒有用 Word 上標（同一份文件裡有的用、有的沒用），
# 但它們是有臨床意義的數值 → 顯示層一律補成 Unicode 上標（坑 #40 的規則）
SUP_FIX = [
    (re.compile(r"/\s*mm\s*3(?![\d])"), "/mm³"),
    (re.compile(r"(\d)\s*mg\s*/\s*m\s*2(?![\d])"), r"\1mg/m²"),
    (re.compile(r"1\.73\s*m\s*2(?![\d])"), "1.73 m²"),
    (re.compile(r"[×x]\s*10\s*9(?![\d])"), "×10⁹"),
    (re.compile(r"(?<=需達)10\s*-\s*3(?![\d])"), "10⁻³"),
]


def fix_superscripts(items):
    n = 0
    for it in items:
        for node, field in [(it, "header")] + [(s, "text") for s in it["subitems"]]:
            t = node[field]
            for rx, rp in SUP_FIX:
                t2 = rx.sub(rp, t)
                if t2 != t:
                    n += 1
                    t = t2
            node[field] = t
    return n


def build_table(d):
    """PD-L1 對照表：DOCX 真表格 → 既有的 table 結構"""
    rows = M.docx_table(DOCX)
    hdr = [c.strip() for c in rows[0]]
    body = rows[1:]
    assert hdr[0].startswith("給付範圍") and hdr[1].startswith("事審代碼"), hdr[:2]
    cols = []
    for h in hdr[2:]:
        m = re.match(r"^([A-Za-z\-]+)\s*[（(]?(.*?)[)）]?$", h.replace("\n", " ").strip())
        cols.append({"drug": m.group(1).strip() if m else h,
                     "assay": (m.group(2).strip() if m and m.group(2) else "")})
    na = "本藥品尚未給付於此適應症"
    out_rows = []
    for r in body:
        scope, code = r[0].strip(), r[1].strip()
        cells = [c.strip() if c.strip() else na for c in r[2:]]
        cs, _ = T.scan_diseases(scope)
        out_rows.append({"scope": scope, "code": code, "cells": cells,
                         "cancerTags": [c for c in T.CANCERS if c in cs] or ["*"]})
    # ⚠ 表尾註不可硬編碼：本版官方把「非小細胞肺癌或泌尿道上皮癌維持療法」
    #   改成「非小細胞肺癌、泌尿道上皮癌維持療法**或食道鱗狀細胞癌**」（坑 #60）
    note = ""
    for para in M.docx_paragraphs(DOCX):
        if "SP263" in para and "僅適用" in para:
            note = para.strip()
            break
    assert note, "找不到 PD-L1 表尾註"
    return {"title": "PD-L1 表現量 / 事審代碼對照表",
            "scopeHeader": hdr[0].strip(), "codeHeader": hdr[1].strip(),
            "columns": cols, "na": na, "note": note, "rows": out_rows}


def main(ship):
    drugs = L.load_drugs(ship)
    D = {d["num"]: d for d in drugs}
    # DOCX 給段落邊界與上標、PDF 只補 Word 自動編號缺的前綴（坑 #60）
    prefix = M.pdf_prefix_by_section(L.read_source(PDF_TXT))
    paras = M.docx_paragraphs(DOCX)
    SEC = P.parse_docx_sections(paras, prefix)

    order = sorted(SEC, key=lambda x: [int(y) for y in x.split(".")[1:]])
    out, cursor = [], 0
    n_new, n_changed, n_same, n_textfix = 0, 0, 0, 0

    for num in order:
        p = SEC[num]
        old = D.get(num)
        if p is None:
            rep.append(f"!! {num} 解析失敗，沿用舊資料")
            out.append(old); continue

        # 父項目（含子藥物 marker）：條文由子項目重建，不在這裡處理
        if old and any(L.is_marker(i) for i in old.get("items", [])):
            out.append(old); n_same += 1; continue

        # 已刪除條號：官方只留「（刪除）」四個字，說明文字是我們寫的 —— 不可被重建覆蓋
        if old and old.get("deleted"):
            old["revisions"] = p["revisions"] or old.get("revisions") or []
            out.append(old); n_same += 1; continue

        items = [{"num": it["num"], "header": it["header"],
                  "subitems": [{"num": s["num"], "text": s["text"]} for s in it["subitems"]]}
                 for it in p["items"]]
        n_sup = fix_superscripts(items)
        if n_sup:
            n_textfix += n_sup

        if old is None:
            # 新藥：name/brand 由標題行解析，types 無法從原文推導 → 留空待人工確認
            raw_title = next((x for x in paras if x.strip().startswith(num + ".")), num)
            m = re.match(r"^9\.\d+(?:\.\d+)?\.\s*(.*?)\s*[（(]如\s*(.*?)\s*[)）]?\s*[）)]?\s*[：:]",
                         re.sub(r"\s+", " ", raw_title))
            name = m.group(1).strip() if m else re.sub(r"^9\.[\d.]+\.\s*", "", raw_title).split("：")[0].strip()
            brand = m.group(2).strip() if m else ""
            # types 無法從條文推導 → 依藥理類別人工指定（與同類藥一致）
            #   9.139 Mogamulizumab = 抗 CCR4 單株抗體，對照 9.56 Brentuximab vedotin（ADC）→ 標靶
            #   9.140 Axicabtagene ciloleucel = CAR-T，對照 9.103 Tisagenlecleucel → 免疫
            TYPES = {"9.139": ["標靶"], "9.140": ["免疫"]}
            d = {"num": num, "name": name, "brand": brand, "cancers": [],
                 "types": TYPES.get(num, []),
                 "pre_review": False, "form_no": p["form_no"], "is_parent": False,
                 "is_real_parent_with_children": False, "review_scope": "none",
                 "review_source": [], "revisions": p["revisions"],
                 "lead": p["lead"], "items": items, "search_text": ""}
            n_new += 1
            rep.append(f"++ 新藥 {num} {name}（{brand}）｜{len(items)} 條｜**types 待人工確認**")
        else:
            d = old
            before = L.norm("".join(
                [(i.get("header") or "") + "".join(s.get("text") or "" for s in i.get("subitems", []))
                 for i in d["items"]]))
            after = L.norm("".join(
                [i["header"] + "".join(s["text"] for s in i["subitems"]) for i in items]))
            # 保留既有表格（下面單獨重建）
            tbl_at = None
            for ii, it in enumerate(d["items"]):
                for si, s in enumerate(it.get("subitems", [])):
                    if s.get("table"):
                        tbl_at = (ii, si)
            d["items"] = items
            d["lead"] = p["lead"]
            d["revisions"] = p["revisions"]
            if p["form_no"] and not d.get("form_no"):
                d["form_no"] = p["form_no"]
            if before != after:
                n_changed += 1
                rep.append(f"~~ {num} {d['name'][:22]}：條文變動（{len(items)} 條）")
            else:
                n_same += 1

        out.append(d)

    # ── PD-L1 對照表：用 DOCX 真表格重建 ──
    d69 = next(x for x in out if x["num"] == "9.69")
    tb = build_table(d69)
    placed = False
    for it in d69["items"]:
        for s in it["subitems"]:
            if "需符合下表" in (s.get("text") or ""):
                s["table"] = tb
                placed = True
    assert placed, "找不到 PD-L1 表格的掛載點"
    rep.append(f"== PD-L1 對照表重建：{len(tb['rows'])} 列 × {len(tb['columns'])} 欄"
               f"（{'、'.join(c['drug'] for c in tb['columns'])}）")

    # ── 父項目條文一律由子項目重建（父落後於子會靜默顯示舊條文，坑 #51）──
    bn = {d["num"]: d for d in out}
    for d in out:
        kids = [bn[k] for k in sorted(bn, key=lambda x: [int(y) for y in x.split(".")[1:]])
                if k.startswith(d["num"] + ".")]
        if not kids:
            continue
        markers = [it for it in d["items"] if L.is_marker(it)]
        new_items = []
        for i, k in enumerate(kids):
            new_items.append(markers[i] if i < len(markers) else {
                "num": "◆", "_is_source_marker": True, "cancerTags": ["*"], "subitems": [],
                "header": f"【{k['num']}　{k['name']}{('（' + k['brand'] + '）') if k.get('brand') else ''}】"})
            new_items += json.loads(json.dumps(k["items"], ensure_ascii=False))
        if json.dumps(d["items"], ensure_ascii=False) != json.dumps(new_items, ensure_ascii=False):
            rep.append(f"   {d['num']} 父項目條文由子項目重建（{len(new_items)} 條）")
        d["items"] = new_items

    # ── 標籤 / cancers / 事審 / search_text 全部重推 ──
    for d in out:
        if d.get("deleted"):
            continue
        want = T.derive_for_drug(d, L.is_marker)
        for ii, it in enumerate(d["items"]):
            it["cancerTags"] = want[(ii, None)][0]
            for si, s in enumerate(it.get("subitems", [])):
                s["cancerTags"] = want[(ii, si)][0]
        newc = T.cancers_from_tags(d)
        if newc:
            if set(newc) != set(d.get("cancers") or []):
                rep.append(f"   {d['num']} cancers：{d.get('cancers')} → {newc}")
            d["cancers"] = newc

    bynum = {d["num"]: d for d in out}
    for d in out:
        kids = [bynum[k] for k in bynum if k.startswith(d["num"] + ".")]
        own = ("事前審查" in L.flat(L.drug_text(d))) or bool(d.get("form_no"))
        if kids:
            kpa = [("事前審查" in L.flat(L.drug_text(k))) or bool(k.get("form_no")) for k in kids]
            d["pre_review"] = own or any(kpa)
            d["review_scope"] = "all" if (own or all(kpa)) else ("partial" if any(kpa) else "none")
        else:
            d["pre_review"] = own
            d["review_scope"] = "all" if own else "none"
        srcs = []
        if "事前審查" in L.flat(L.drug_text(d)):
            srcs.append("explicit_text")
        if d.get("form_no"):
            srcs.append("appendix_reference")
        if kids and any(("事前審查" in L.flat(L.drug_text(k))) or bool(k.get("form_no")) for k in kids) \
                and "事前審查" not in L.flat(L.drug_text(d)):
            srcs.append("inherited_child")
        d["review_source"] = srcs
        L.rebuild_search_text(d)

    L.save_drugs(ship, out)
    rep.insert(0, f"藥品 {len(out)}（新增 {n_new}）｜條文變動 {n_changed}｜未變動 {n_same}"
                  f"｜由 DOCX 修正文字 {n_textfix} 處")
    Path("report_update.txt").write_text("\n".join(rep), encoding="utf-8")
    print("\n".join(rep[:40]))
    print(f"\n-> 已寫回 {ship}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "index.html")
