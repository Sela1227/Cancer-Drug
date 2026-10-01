#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共用底層模組（V5.9.0 起隨 repo 一起版控）

為什麼腳本要進 repo：CLAUDE.md 寫著「跑 validate.py，BLOCK 必須為 0」，
但腳本若只存在於對話端，規範就指向一個沒人拿得到的東西（坑 #58）。
"""
import json, re, sys, unicodedata
from pathlib import Path

# ---------- 出版檔的 drugs 陣列 ----------
MARK_BEGIN = "const drugs = ["
MARK_END = "];"


def load_drugs(path):
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    a = next(i for i, l in enumerate(lines) if l.startswith(MARK_BEGIN))
    b = next(i for i in range(a, len(lines)) if lines[i].strip() == MARK_END)
    raw = "\n".join(lines[a:b + 1]).replace(MARK_BEGIN, "[", 1).rstrip()[:-1]
    return json.loads(raw)


def save_drugs(path, drugs):
    """寫回 index.html，只置換 drugs 陣列（絕不動其他任何一行）"""
    p = Path(path)
    lines = p.read_text(encoding="utf-8").split("\n")
    a = next(i for i, l in enumerate(lines) if l.startswith(MARK_BEGIN))
    b = next(i for i in range(a, len(lines)) if lines[i].strip() == MARK_END)
    new = (MARK_BEGIN[:-1] + json.dumps(drugs, ensure_ascii=False, indent=2) + ";").split("\n")
    lines[a:b + 1] = new
    p.write_text("\n".join(lines), encoding="utf-8")


# ---------- 健保署原文 ----------
PAGEBREAK = re.compile(r"第9節-\d+")
SECTION = re.compile(r"^\s{0,3}(9\.\d+(?:\.\d+)?)\.\s*", re.M)
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


MD_BOLD = re.compile(r"\*\*")
MD_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
MD_TABLE_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def read_source(path, flatten_tables=True):
    """健保署第九節檔。

    兩種來源格式都支援（副檔名不可信，一律看內容）：
      · 舊：PDF 抽出的純文字（頁碼雜訊多、表格壓平、條文會跨行截斷）
      · 新：docx 轉出的 Markdown（`**` 粗體、`|…|` 表格、無截斷）  ← 優先採用

    flatten_tables=True 時把 Markdown 表格攤平成一行文字，讓既有的
    逐句比對工具（diff_source）沿用同一套邏輯；需要表格結構時改用
    read_md_tables() 直接取 rows/cells。
    """
    if str(path).lower().endswith(".docx") and Path(path).read_bytes()[:2] == b"PK":
        # 真 OOXML：段落（上標還原）+ 表格攤平，與出版檔的結構一致
        import sys as _s
        _s.path.insert(0, str(Path(__file__).resolve().parent))
        import merge_sources as _M
        parts = _M.docx_paragraphs(path)
        if flatten_tables:
            for row in _M.docx_table(path):
                parts.append("".join(row))
        return "\n".join(parts)
    t = Path(path).read_text(encoding="utf-8", errors="replace")
    t = PAGEBREAK.sub("", t)
    t = MD_BOLD.sub("", t)                      # 粗體標記不是條文內容
    if flatten_tables:
        out = []
        for ln in t.split("\n"):
            if MD_TABLE_SEP.match(ln):
                continue                        # | --- | --- | 分隔列丟掉
            if MD_TABLE_ROW.match(ln):
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                out.append("".join(cells))      # 攤平成與舊格式同形的連續文字
            else:
                out.append(ln)
        t = "\n".join(out)
    return t


def read_md_tables(path):
    """取出 Markdown 表格的結構：[{header:[...], rows:[[...],...]}]"""
    t = MD_BOLD.sub("", Path(path).read_text(encoding="utf-8", errors="replace"))
    tables, cur = [], None
    for ln in t.split("\n"):
        if MD_TABLE_ROW.match(ln):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if MD_TABLE_SEP.match(ln):
                continue
            if cur is None:
                cur = {"header": cells, "rows": []}
            else:
                cur["rows"].append(cells)
        else:
            if cur is not None:
                tables.append(cur)
                cur = None
    if cur is not None:
        tables.append(cur)
    return tables


def split_sections(text):
    """切成 {條號: 該條全文}；條號順序即官方順序"""
    ms = list(SECTION.finditer(text))
    out = {}
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out[m.group(1)] = text[m.start():end]
    return out


# ---------- 正規化 ----------
# 顯示層用 Unicode 上標，原文是拉平的；比對前要還原（坑 #51）
UNSUP = [("mm³", "mm3"), ("m²", "m2"), ("10⁻³", "10-3"), ("×10⁹", "×109")]
SUPMAP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
DATE_PAREN = re.compile(r"[（(][0-9０-９/、\s]+[)）]")
DATE_BARE = re.compile(r"\d{2,3}/\d{1,2}/\d{1,2}")
# ⚠ NFKC 把上標負號 ⁻(U+207B) 轉成 −(U+2212)，不是 ASCII '-'（坑 #51）
PUNCT = re.compile(r"[，,。、；;：:！!？?（）()「」『』【】\[\]〔〕．·・\-–—−‧※*]")


def flat(s):
    """去空白 + NFKC；保留標點。用於「是否逐字出現」的寬鬆比對"""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", CTRL.sub("", s or "")))


def norm(s, drop_dates=True):
    """比對基準：去空白、還原上標、去日期、去標點、小寫"""
    t = CTRL.sub("", s or "")
    t = unicodedata.normalize("NFKC", t)
    for a, b in UNSUP:
        t = t.replace(a, b)
    t = t.translate(SUPMAP)
    if drop_dates:
        t = DATE_PAREN.sub("", t)
        t = re.sub(r"[（(][0-9０-９/、\s]*$", "", t)   # 跨行截斷的未閉合日期括號
        t = DATE_BARE.sub("", t)
    t = re.sub(r"\s+", "", t)
    return PUNCT.sub("", t).lower()


def is_marker(item):
    """子藥物標題【9.x.y …】是我們合成的分隔標記，不是原文條文"""
    return bool(item.get("_is_source_marker")) or \
        (item.get("header") or "").lstrip().startswith("【")


def drug_nodes(d, include_notes=False):
    """走訪一支藥的所有文字節點：(標籤, 節點, 欄位名)"""
    for it in d.get("items", []):
        yield f"item {it['num']}", it, "header"
        for s in it.get("subitems", []):
            yield f"{it['num']}/{s['num']}", s, "text"


def drug_text(d, include_notes=False, skip_markers=True):
    """一支藥的完整條文文字（表格展平；預設不含我們自己加的註記）"""
    parts = [d.get("lead") or ""]
    for it in d.get("items", []):
        if skip_markers and is_marker(it):
            continue
        parts.append(it.get("header") or "")
        for s in it.get("subitems", []):
            parts.append(s.get("text") or "")
            tb = s.get("table")
            if tb:
                parts.append((tb.get("scopeHeader") or "") + (tb.get("codeHeader") or ""))
                parts += [c["drug"] + c["assay"] for c in tb["columns"]]
                for r in tb["rows"]:
                    parts.append(r["scope"] + r["code"] + "".join(r["cells"]))
                    if include_notes and r.get("rowNote"):
                        parts.append(r["rowNote"])
                parts.append(tb["note"])
            if include_notes and s.get("xrefNote"):
                parts.append(s["xrefNote"])
    return "\n".join(parts)


NA_DEFAULT = "本藥品尚未給付於此適應症"


def rebuild_search_text(d):
    """search_text 是衍生索引，改過條文就要重生（Kit 坑 #47）"""
    parts = [d.get("name") or "", d.get("brand") or "", d.get("lead") or ""]
    for it in d.get("items", []):
        parts.append(it.get("header") or "")
        for s in it.get("subitems", []):
            parts.append(s.get("text") or "")
            tb = s.get("table")
            if tb:
                na = tb.get("na", NA_DEFAULT)
                for r in tb["rows"]:
                    parts.append(r["scope"] + " " + r["code"] + " " +
                                 " ".join(c for c in r["cells"] if c != na))
                    if r.get("rowNote"):
                        parts.append(r["rowNote"])
                parts.append(tb["note"])
                parts += [c["drug"] for c in tb["columns"]]
            if s.get("xrefNote"):
                parts.append(s["xrefNote"])
    parts += list(d.get("cancers") or []) + list(d.get("revisions") or [])
    d["search_text"] = " ".join(x for x in parts if x).lower()


def default_source():
    """預設取 project 內最新的第九節檔"""
    cands = sorted(Path("/mnt/project").glob("chap9_*.pdf"))
    return str(cands[-1]) if cands else ""


def resolve_args(argv, need_source=True):
    ship = argv[1] if len(argv) > 1 else "index.html"
    src = argv[2] if len(argv) > 2 else default_source()
    if need_source and not src:
        print("找不到健保署原文檔，請以第二個參數指定", file=sys.stderr)
        sys.exit(2)
    return ship, src
