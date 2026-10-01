#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把官方原文的一個 9.X 段落解析成 items / subitems 結構。

只在「新格式（docx→markdown）」上使用：它以空行分段、條文不跨行截斷，
所以解析規則可以很單純 —— 不要拿去解析舊的 PDF 抽取文字。

紀律（坑 #58）：改條文前先用 --verify 證明這支 parser 能重現未變動的條文，
等價了才拿去重建變動的條文。
"""
import re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib_drugs as L

ITEM = re.compile(r"^\s*([0-9０-９]{1,3})\s*[.、]\s*(.*)$", re.S)
SUB = re.compile(r"^\s*[（(]\s*([0-9０-９]{1,3})\s*[)）]\s*(.*)$", re.S)
ROMAN = re.compile(r"^\s*(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]|[IVX]{1,4}|[ⅰⅱⅲⅳⅴ]|[ivx]{1,4})[.、]")
FORM = re.compile(r"附表[一二三四五六七八九十之\d]+")
TITLE_DATE = re.compile(r"[（(]\s*([0-9０-９][0-9０-９/、\s]*)[)）]")


def _feed(cur, p):
    """把一個段落餵進目前的條號；缺編號時從 PDF 前綴序列補"""
    import merge_sources as _M
    cur["raw"].append(p)
    if not ITEM.match(p) and not SUB.match(p) and not ROMAN.match(p):
        pre = _M.take_prefix(cur["pairs"], p, cur["used"])
        if pre:
            p = pre + p
    m_sub, m_item = SUB.match(p), ITEM.match(p)
    if m_sub and cur["items"]:
        cur["items"][-1]["subitems"].append(
            {"num": f"({m_sub.group(1)})", "text": m_sub.group(2).strip()})
    elif m_item:
        cur["items"].append({"num": m_item.group(1),
                             "header": m_item.group(2).strip(), "subitems": []})
    elif cur["items"]:
        # 羅馬數字層級與續段：黏回最後一個節點（顯示層會再做換行縮排）
        if cur["items"][-1]["subitems"]:
            cur["items"][-1]["subitems"][-1]["text"] += " " + p
        else:
            cur["items"][-1]["header"] += " " + p
    else:
        cur["lead_parts"].append(p)


def parse_docx_sections(paras, prefix_by_sec):
    """以 DOCX 段落為結構主體，對缺編號的段落從 PDF 索引補前綴（坑 #60）。

    DOCX 的段落邊界可靠（無跨行截斷），但 Word 自動編號不在 p.text 裡；
    PDF 保留編號前綴但是硬換行無法整段解析 —— 各取所長。
    回傳 {條號: parse_section 同形的 dict}
    """
    SECHEAD = re.compile(r"^\s*(9\.\d+(?:\.\d+)?)\.")
    out, cur, num = {}, None, None
    for raw in paras:
        p = raw.strip()
        if not p:
            continue
        m = SECHEAD.match(p)
        if m:
            if cur is not None:
                out[num] = cur
            num = m.group(1)
            # DOCX 可能把標題行與第 1 項擠在同一段（段內 \n 分隔，如 9.63）
            # → 必須拆開，否則第 1 項整條被吞掉
            head, *rest = p.split("\n")
            cur = {"title": head.strip(), "lead_parts": [], "items": [], "raw": [head.strip()],
                   "pairs": prefix_by_sec.get(num, []), "used": set()}
            pending = [r.strip() for r in rest if r.strip()]
            for q in pending:
                _feed(cur, q)
            continue
        if cur is None:
            continue
        _feed(cur, p)
    if cur is not None:
        out[num] = cur

    for n, c in out.items():
        seg = "\n".join(c["raw"])
        lead = "".join(c["lead_parts"])
        items = c["items"]
        if not items and lead:
            items = [{"num": "1", "header": lead, "subitems": []}]
            lead = ""
        form = FORM.search(seg)
        c.clear()
        c.update({"title": n, "lead": lead, "items": items,
                  "revisions": sorted(set(re.findall(r"\d{2,3}/\d{1,2}/\d{1,2}", L.flat(seg))),
                                      key=lambda s: tuple(int(x) for x in s.split("/"))),
                  "form_no": form.group(0) if form else ""})
    return out


def parse_section(seg):
    """回傳 dict(title=…, lead=…, items=[…], revisions=[…], form_no=…)"""
    paras = [p.strip() for p in re.split(r"\n\s*\n", seg) if p.strip()]
    if not paras:
        return None
    title = paras[0]
    body = paras[1:]

    # 標題行可能與第一條黏在同一段（例如「…：\n1.限…」）
    if "\n" in title:
        head, rest = title.split("\n", 1)
        if ITEM.match(rest.strip()) or SUB.match(rest.strip()):
            title = head
            body = [rest.strip()] + body

    form = FORM.search(seg)
    revisions = sorted(set(re.findall(r"\d{2,3}/\d{1,2}/\d{1,2}", L.flat(seg))),
                       key=lambda s: tuple(int(x) for x in s.split("/")))

    lead_parts, items = [], []
    for p in body:
        p = re.sub(r"\s*\n\s*", "", p)        # 段內換行是排版，不是內容
        m_sub = SUB.match(p)
        m_item = ITEM.match(p)
        if m_sub and items:
            items[-1]["subitems"].append({"num": f"({m_sub.group(1)})",
                                          "text": m_sub.group(2).strip()})
        elif m_item:
            items.append({"num": m_item.group(1), "header": m_item.group(2).strip(),
                          "subitems": []})
        elif items:
            # 續段：黏回最後一個節點
            if items[-1]["subitems"]:
                items[-1]["subitems"][-1]["text"] += p
            else:
                items[-1]["header"] += p
        else:
            lead_parts.append(p)              # 第一條之前 = 無編號前導句

    lead = "".join(lead_parts)
    # 整段只有一句無編號條文（如 9.6、9.8、9.5.2）：那句就是全部內容，
    # 必須當 item 顯示，不能只存在 lead（否則畫面什麼都沒有）。
    # 這與坑 #50 的三支（9.19/9.68/9.86）不同 —— 那些是「前導句 + 官方 1./2./3.」。
    if not items and lead:
        items = [{"num": "1", "header": lead, "subitems": []}]
        lead = ""

    return {"title": title, "lead": lead,
            "items": items, "revisions": revisions,
            "form_no": form.group(0) if form else ""}


def verify(ship, src, limit=None):
    """用未變動的條文證明 parser 等價：解析結果的文字應與出版檔逐字相同"""
    drugs = {d["num"]: d for d in L.load_drugs(ship)}
    SEC = L.split_sections(L.read_source(src))
    same, diff, skipped = [], [], []
    for num, seg in SEC.items():
        d = drugs.get(num)
        if not d or d.get("deleted") or any(L.is_marker(i) for i in d.get("items", [])):
            skipped.append(num); continue      # 新藥／已刪除／父項目另外處理
        p = parse_section(seg)
        if not p:
            skipped.append(num); continue
        got = L.norm("".join(
            [it["header"] + "".join(s["text"] for s in it["subitems"]) for it in p["items"]]))
        want = L.norm("".join(
            [(it.get("header") or "") + "".join(s.get("text") or "" for s in it.get("subitems", []))
             for it in d["items"]]))
        (same if got == want else diff).append(num)
    print(f"parser 等價驗證：相同 {len(same)}｜不同 {len(diff)}｜略過 {len(skipped)}")
    if diff:
        print("  不同的條號（＝本次真的有內容變動，或 parser 需修）：")
        print("   ", " ".join(diff[:40]))
    return same, diff, skipped


if __name__ == "__main__":
    ship = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    src = sys.argv[2] if len(sys.argv) > 2 else "/mnt/project/chap9_1150922.docx"
    verify(ship, src)
