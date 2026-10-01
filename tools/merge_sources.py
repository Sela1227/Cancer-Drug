#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合併兩種官方來源，各取所長（V5.10.0 起的標準做法）：

  · PDF 文字  → **條號層級的真相**（1. / (1) / Ⅰ.）
                DOCX 的自動編號存在 numbering.xml，`p.text` 讀不到，
                而重建 34 組零碎 numId 的邏輯很脆弱、且沒有閘門抓得到算錯（坑 #60）
  · DOCX      → **句子內容與數值的真相**
                無跨行截斷（PDF 有 162 處）、無中文字間空白（PDF 有 1,214 處）、
                **上標是真的 run**（mg/m² mm³ 10⁻³ ×10⁹，共 13 處）

做法：兩份來源的段落順序完全相同 → 以「正規化文字 + 單調順序」對齊，
把 PDF 的編號前綴貼到 DOCX 的文字上。對不齊的節點一律保留 PDF 原樣並列入報告，
**不猜**。
"""
import re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib_drugs as L

SUP_MAP = str.maketrans("0123456789+-=()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾")


def docx_paragraphs(path):
    """抽出 DOCX 段落文字，上標 run 轉成 Unicode 上標字元"""
    import docx
    d = docx.Document(path)
    out = []
    for p in d.paragraphs:
        buf = []
        for r in p.runs:
            t = r.text
            if t and r.font.superscript:
                t = t.translate(SUP_MAP)
            buf.append(t)
        s = "".join(buf).strip()
        if s:
            out.append(s)
    return out


def docx_table(path, index=0):
    """抽出 DOCX 表格（真表格，不是壓平文字）"""
    import docx
    d = docx.Document(path)
    tb = d.tables[index]
    rows = []
    for r in tb.rows:
        rows.append([c.text.replace("\n", " ").strip() for c in r.cells])
    return rows


def key(s, n=24):
    """對齊用指紋：去空白標點、去日期、取前 n 字"""
    return L.norm(s)[:n]


def align(pdf_nodes, dx_paras, start_hint=0, window=60):
    """把 pdf_nodes 的每個文字對齊到 dx_paras，回傳 [(idx or None)]

    單調推進 + 視窗限制：順序相同的兩份文件，對齊只需往前找。
    """
    res, j = [], start_hint
    for txt in pdf_nodes:
        k = key(txt)
        hit = None
        if len(k) >= 8:
            for jj in range(j, min(j + window, len(dx_paras))):
                if key(dx_paras[jj]).startswith(k[:min(len(k), 18)]) or \
                   k.startswith(key(dx_paras[jj])[:18]):
                    hit = jj
                    break
        res.append(hit)
        if hit is not None:
            j = hit + 1
    return res, j


def pdf_prefix_by_section(pdf_text):
    """分節建立「編號前綴序列」。

    ⚠ 不可用全域索引：「需經事前審查核准後使用」這類句子全文出現數十次，
    全域索引會把第一次出現的前綴套到所有地方（9.82 實測編號全錯）。
    改為每個 9.X 段落各自一份、且同句重複時依出現順序消耗。
    """
    secs = L.split_sections(pdf_text)
    out = {}
    for num, seg in secs.items():
        pairs = []
        lines = seg.split("\n")
        for i, ln in enumerate(lines):
            m = _PREFIX.match(ln)
            if not m:
                continue
            rest = m.group(2).strip()
            j = i + 1
            while len(L.norm(rest)) < 16 and j < len(lines) and j < i + 4:
                nxt = lines[j].strip()
                if _PREFIX.match(nxt):
                    break
                rest += nxt
                j += 1
            k = L.norm(rest)[:16]
            if len(k) >= 8:
                pairs.append((k, m.group(1).strip()))
        out[num] = pairs
    return out


def take_prefix(pairs, text, used):
    """從該節的前綴序列取出對應編號；同句重複時依順序消耗"""
    k = L.norm(text)[:16]
    if len(k) < 8:
        return None
    for i, (kk, pre) in enumerate(pairs):
        if i in used:
            continue
        if kk == k or kk.startswith(k[:12]) or k.startswith(kk[:12]):
            used.add(i)
            return pre
    return None


_PREFIX = re.compile(r"^\s*((?:[0-9０-９]{1,3}[.、])|(?:[（(][0-9０-９]{1,3}[)）])"
                     r"|(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ][.、])|(?:[IVX]{1,4}[.、])"
                     r"|(?:[ⅰⅱⅲⅳⅴ][.、])|(?:[ivx]{1,4}[.、]))\s*(.*)$")


def pdf_prefix_index(pdf_text):
    """建立 PDF 的「正規化句首 → 編號前綴」索引。

    PDF 是硬換行格式，無法整段解析（parse_section 只適用 DOCX 分段），
    但它保留了編號前綴 —— 所以只拿它來補 DOCX 缺的那 128 個自動編號。
    """
    PREFIX = re.compile(r"^\s*((?:[0-9０-９]{1,3}[.、])|(?:[（(][0-9０-９]{1,3}[)）])"
                        r"|(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ][.、])|(?:[IVX]{1,4}[.、])"
                        r"|(?:[ⅰⅱⅲⅳⅴ][.、])|(?:[ivx]{1,4}[.、]))\s*(.*)$")
    idx = {}
    lines = pdf_text.split("\n")
    for i, ln in enumerate(lines):
        m = PREFIX.match(ln)
        if not m:
            continue
        rest = m.group(2).strip()
        # 內容可能續到下一行，補到夠長再當指紋
        j = i + 1
        while len(L.norm(rest)) < 16 and j < len(lines) and j < i + 4:
            nxt = lines[j].strip()
            if PREFIX.match(nxt):
                break
            rest += nxt
            j += 1
        k = L.norm(rest)[:16]
        if len(k) >= 8 and k not in idx:
            idx[k] = m.group(1).strip()
    return idx


def report(path, lines):
    Path(path).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    pdf_txt = sys.argv[1] if len(sys.argv) > 1 else "src_0922.txt"
    docx_p = sys.argv[2] if len(sys.argv) > 2 else "/mnt/user-data/uploads/chap9_1150922.docx"
    paras = docx_paragraphs(docx_p)
    tb = docx_table(docx_p)
    sup = [p for p in paras if any(c in p for c in "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")]
    print(f"DOCX 段落 {len(paras)}｜含 Unicode 上標的段落 {len(sup)}｜表格 {len(tb)}×{len(tb[0])}")
    for s in sup[:8]:
        m = re.search(r".{0,34}[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+.{0,10}", s)
        print("   ", m.group(0) if m else s[:50])
