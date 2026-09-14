#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
115/8/21 公告條文更新（生效日 115/8/1、115/9/1）。

兩層 diff 結果：條號層 153→153 無增減；內容層 6 條變動，其中 9.45 / 9.53
為純排版（斷行位置），實質變動 4 條：9.4 / 9.20 / 9.43 / 9.69。

所有新條文文字均逐字取自 chap9_1150821.pdf，不改寫、不補字。
用法：python3 tools/update_1150821.py [index.html] [新原文]
"""
import re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib_drugs as L
import derive_tags as T

rep = []


def sec_text(SEC, num):
    return SEC[num]


def dates_in(seg, head_only=True):
    """取藥品標題行（到第一個換行後的日期括號結束）的修訂日"""
    flat = L.flat(seg)
    m = re.match(r"^9\.\d+(?:\.\d+)?\..*?[（(]([0-9０-９/、]+)[)）]", flat)
    return re.findall(r"\d{2,3}/\d{1,2}/\d{1,2}", flat)


def refresh_revisions(d, seg):
    """revisions = 標題括號 ∪ 條文全文日期，去重後依年月日排序（坑 #50）"""
    alld = set(re.findall(r"\d{2,3}/\d{1,2}/\d{1,2}", L.flat(seg)))
    old = set(d.get("revisions") or [])
    merged = sorted(alld | old, key=lambda s: tuple(int(x) for x in s.split("/")))
    if merged != (d.get("revisions") or []):
        add = sorted(alld - old, key=lambda s: tuple(int(x) for x in s.split("/")))
        if add:
            rep.append(f"  revisions {d['num']}：+{add}（共 {len(merged)} 筆）")
        d["revisions"] = merged


def main(ship, src):
    drugs = L.load_drugs(ship)
    D = {d["num"]: d for d in drugs}
    SEC = L.split_sections(L.read_source(src))

    # ───────── 9.4 Gemcitabine：Gemmis 獨立限制整段刪除，併回通則（115/9/1）─────────
    d = D["9.4"]
    rep.append("【9.4 Gemcitabine】Gemmis 專屬限制整段刪除，第 1 項改為適用全部品項")
    d["items"] = [{
        "num": "1",
        "header": ("本類藥品依藥品許可證登載之適應症範圍內給付於非小細胞肺癌、胰臟癌、膀胱癌、乳"
                   "癌、卵巢癌及膽道癌之病例；倘併用其他標靶治療、免疫檢查點抑制劑等藥品時，病人"
                   "須符合該併用藥品之藥品給付規定。"),
        "subitems": [],
    }]
    rep.append("  舊第 2 項（Gemmis 限給付 7 款）連同其子項一併移除")

    # ───────── 9.20 Rituximab：品牌限制由「限 Rixathon」改為「除 Mabthera 以外」─────────
    d = D["9.20"]
    rep.append("【9.20 Rituximab】品牌限制反轉；事審規則改為品牌×適應症交叉")
    it5 = next(i for i in d["items"] if i["num"] == "5")
    s51 = next(s for s in it5["subitems"] if s["num"] == "(1)")
    s51["text"] = ("Rai Stage Ⅲ/Ⅳ(或 Binet C 級)之 CLL 病人。若用於 Rai StageⅠ/Ⅱ(或 Binet "
                   "A/B 級)併有疾病相關免疫性症候(如自體免疫性溶血、免疫性血小板低下紫瘢症"
                   "等)的病人時，需經過至少一種標準的烷化基劑治療無效或病情惡化者，且 CD20"
                   "陽性細胞須大於50%。（除 Mabthera 以外，不受「需經過一種標準的烷化基劑治"
                   "療無效或病情惡化，且 CD20陽性細胞須大於50%」限制，僅須符合具 CD20陽性細"
                   "胞即可使用，做為第一線用藥需與 fludarabine 及 cyclophosphamide 併用）")
    rep.append("  5(1)：「Rixathon 不受…限制」→「除 Mabthera 以外，不受…限制」")
    s52 = next(s for s in it5["subitems"] if s["num"] == "(2)")
    s52["text"] = ("與化學療法併用，做為復發或頑固性的 CD20陽性慢性淋巴球性白血病病患的治療"
                   "用藥，且 CD20陽性細胞須大於50%。（除 Mabthera 以外，不受「CD20陽性細胞須"
                   "大於50%」限制，僅須符合具 CD20陽性細胞即可使用）")
    rep.append("  5(2)：同上反轉")
    it9 = next(i for i in d["items"] if i["num"] == "9")
    it9["header"] = ("Rituximab(除 Mabthera 以外)合併 lenalidomide(限使用 Revlimid 及 Leavdo)用於"
                     "先前曾接受至少一線全身性治療之復發性或難治性濾泡性淋巴瘤成人病人，需符合"
                     "lenalidomide 之藥品給付規定。")
    rep.append("  第 9 項：「限使用 Rixathon」→「除 Mabthera 以外」；lenalidomide 加 Leavdo")
    it10 = next(i for i in d["items"] if i["num"] == "10")
    it10["header"] = ("Rituximab 用於6、7、8、9及 Mabthera 用於1、4、5，需經事前審查核准後使用。")
    rep.append("  第 10 項事審規則重寫：由「1/4/5/6/7/8/9 需事審、Rixathon 用於 1/4/5 除外」"
               "→「Rituximab 用於 6/7/8/9 及 Mabthera 用於 1/4/5 需事審」")

    # ───────── 9.43 Lenalidomide：品牌清單擴充 ─────────
    d = D["9.43"]
    rep.append("【9.43 Lenalidomide】品牌清單擴充")
    it3 = next(i for i in d["items"] if i["num"] == "3")
    it3["header"] = ("Lenalidomide(限使用 Revlimid 及 Leavdo)與 rituximab(除 Mabthera 以外)併用，治"
                     "療先前曾接受至少一線全身性治療之復發性或難治性濾泡性淋巴瘤成人病人：")
    rep.append("  第 3 項：lenalidomide 加 Leavdo；rituximab「限 Rixathon」→「除 Mabthera 以外」")

    # ───────── 9.69 免疫檢查點抑制劑 ─────────
    d = D["9.69"]
    rep.append("【9.69 免疫檢查點抑制劑】")
    # (a) 術前輔助補 Alimta Avos —— 官方修正了與 9.26 的自我矛盾（坑 #50 ①）
    fixed_a = False
    for it in d["items"]:
        for s in it.get("subitems", []):
            t = s.get("text") or ""
            if "術前輔助治療" in t and "Pexeda" in t:
                new = t.replace("Pexeda、Apeta 或 Pemetrexed Sandoz",
                                "Pexeda、Apeta、Pemetrexed Sandoz 或 Alimta Avos")
                assert new != t, "術前輔助條文替換失敗"
                s["text"] = new
                s.pop("xrefNote", None)      # 官方已修正 → 交叉差異註記功成身退
                fixed_a = True
                rep.append("  (2)I.i 非鱗狀術前輔助：補上 Alimta Avos（官方修正了與 9.26 的不一致）")
                rep.append("        → 移除 V5.6.0 的 xrefNote 交叉差異註記")
    assert fixed_a

    # (b) PD-L1 對照表新增 dostarlimab 欄；P151 填「不需檢附報告」
    tb = None
    for it in d["items"]:
        for s in it.get("subitems", []):
            if s.get("table"):
                tb = s["table"]
    assert tb is not None and len(tb["columns"]) == 6, "PD-L1 表結構非預期"
    tb["columns"].append({"drug": "dostarlimab", "assay": ""})
    na = tb["na"]
    for r in tb["rows"]:
        r["cells"].append("不需檢附報告" if r["code"] == "P151" else na)
        if r["code"] == "P151":
            r.pop("rowNote", None)           # 官方已補欄位 → 註記功成身退
            r["cancerTags"] = ["婦癌"]
    rep.append(f"  PD-L1 對照表：6 → 7 欄，新增 dostarlimab；{len(tb['rows'])} 列各補一格")
    rep.append("  P151 子宮內膜癌：dostarlimab =「不需檢附報告」（官方本版補上）")
    rep.append("        → 移除 V5.6.0 的 rowNote 說明註記")

    # (c) 藥品清單納入 dostarlimab 製劑
    seg69 = L.flat(SEC["9.69"])
    assert "dostarlimab製劑" in seg69
    if "dostarlimab" not in (d.get("name") or ""):
        d["name"] = d["name"].replace("cemiplimab 製劑", "cemiplimab 製劑；dostarlimab 製劑") \
            if "cemiplimab 製劑" in d["name"] else d["name"]
        rep.append(f"  藥品清單納入 dostarlimab 製劑 → name: {d['name'][:60]}…")

    # ───────── 全庫：修訂日期重新抽取 ─────────
    for d in drugs:
        seg = SEC.get(d["num"])
        if seg:
            refresh_revisions(d, seg)

    # ───────── 受影響藥品：重推標籤 + 重算 cancers / search_text ─────────
    for num in ("9.4", "9.20", "9.43", "9.69"):
        d = D[num]
        want = T.derive_for_drug(d, L.is_marker)
        for ii, it in enumerate(d["items"]):
            it["cancerTags"] = want[(ii, None)][0]
            for si, s in enumerate(it.get("subitems", [])):
                s["cancerTags"] = want[(ii, si)][0]
        newc = T.cancers_from_tags(d)
        if newc and set(newc) != set(d.get("cancers") or []):
            rep.append(f"  {num} cancers：{d.get('cancers')} → {newc}")
            d["cancers"] = newc
    for d in drugs:
        L.rebuild_search_text(d)

    L.save_drugs(ship, drugs)
    Path("report_update.txt").write_text("\n".join(rep), encoding="utf-8")
    print("\n".join(rep))
    print(f"\n-> 已寫回 {ship}；報告 report_update.txt")


if __name__ == "__main__":
    ship = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    src = sys.argv[2] if len(sys.argv) > 2 else "/mnt/project/chap9_1150821.pdf"
    main(ship, src)
