#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cancerTags 推導規則 —— 這支是「癌別標籤怎麼來」的唯一真相（坑 #39、#53）。

推導優先序：
  1. 行政共通條文 -> ["*"]（universal-rule）
  2. 病名辨識 -> 對應癌別（text-rule）
  3. 都標不到 -> ["*"]（fallback-unclassified；畫面同為 *，但建置端分流記帳）

核心語意規則（比關鍵字表更重要）：
  · 條文標題自己指明癌別 -> 該條就是那個適應症，子項是它的附帶條件（子項一律 *）
  · 標題沒指明癌別（傘狀/行政條文）-> 整條 *，篩選交給子項各自的標籤
"""
import re, unicodedata

CANCERS = ["乳癌", "肺癌", "食道癌", "大腸直腸癌", "血液淋巴癌", "婦癌",
           "肝膽胰胃癌", "泌尿癌", "頭頸癌", "其他癌"]

# 病名 -> 癌別。長詞優先並逐一消耗，所以「胃食道接合處」不會被當成食道癌。
# 器官單詞（卵巢/子宮頸/睪丸…）一律用 "re:" 正則且要求帶癌症字尾，
# 否則「卵巢切除後」「卵巢功能抑制」會被誤標婦癌（坑 #39）。
DISEASES = [
    ("胃食道接合處", ["肝膽胰胃癌"]), ("食道胃接合處", ["肝膽胰胃癌"]),
    ("非小細胞肺癌", ["肺癌"]), ("小細胞肺癌", ["肺癌"]), ("肺腺癌", ["肺癌"]),
    ("肺癌", ["肺癌"]), ("nsclc", ["肺癌"]), ("sclc", ["肺癌"]),
    ("食道鱗狀細胞癌", ["食道癌"]), ("食道腺癌", ["食道癌"]), ("食道癌", ["食道癌"]),
    ("頭頸部鱗狀細胞癌", ["頭頸癌"]), ("頭頸癌", ["頭頸癌"]),
    (r"re:頭頸部(?:癌|鱗狀|腫瘤)", ["頭頸癌"]),
    ("鼻咽癌", ["頭頸癌"]), ("口腔癌", ["頭頸癌"]), ("口咽癌", ["頭頸癌"]),
    ("下咽癌", ["頭頸癌"]), ("喉癌", ["頭頸癌"]), (r"re:唾液腺(?:癌|腫瘤)", ["頭頸癌"]),
    ("三陰性乳癌", ["乳癌"]), ("分泌型乳腺癌", ["乳癌"]), ("乳腺癌", ["乳癌"]),
    ("乳癌", ["乳癌"]), ("tnbc", ["乳癌"]),
    ("大腸直腸癌", ["大腸直腸癌"]), ("結腸直腸癌", ["大腸直腸癌"]),
    ("直腸結腸癌", ["大腸直腸癌"]), ("大腸癌", ["大腸直腸癌"]),
    ("結腸癌", ["大腸直腸癌"]), ("直腸癌", ["大腸直腸癌"]),
    ("闌尾癌", ["大腸直腸癌", "其他癌"]),
    ("肝細胞癌", ["肝膽胰胃癌"]), ("肝內膽管癌", ["肝膽胰胃癌"]),
    ("膽道癌", ["肝膽胰胃癌"]), ("膽管癌", ["肝膽胰胃癌"]), ("肝癌", ["肝膽胰胃癌"]),
    ("胰臟癌", ["肝膽胰胃癌"]), ("胰腺癌", ["肝膽胰胃癌"]), ("壺腹癌", ["肝膽胰胃癌"]),
    ("胃腺癌", ["肝膽胰胃癌"]), ("胃癌", ["肝膽胰胃癌"]), ("hcc", ["肝膽胰胃癌"]),
    ("泌尿道上皮癌", ["泌尿癌"]), ("尿路上皮癌", ["泌尿癌"]),
    ("腎細胞癌", ["泌尿癌"]), ("腎癌", ["泌尿癌"]), ("膀胱癌", ["泌尿癌"]),
    ("前列腺癌", ["泌尿癌"]), ("攝護腺癌", ["泌尿癌"]),
    (r"re:睪丸(?:癌|腫瘤|生殖細胞)", ["泌尿癌"]),
    ("mcrpc", ["泌尿癌"]), ("mcspc", ["泌尿癌"]), ("crpc", ["泌尿癌"]),
    ("子宮內膜癌", ["婦癌"]), ("子宮體癌", ["婦癌"]),
    (r"re:子宮頸(?:癌|部癌)", ["婦癌"]),
    (r"re:卵巢(?:癌|上皮|及輸卵管|、輸卵管|或輸卵管)", ["婦癌"]),
    (r"re:輸卵管(?:癌|或原發性腹膜)", ["婦癌"]),
    ("原發性腹膜癌", ["婦癌"]), ("陰道癌", ["婦癌"]), ("外陰癌", ["婦癌"]),
    ("蕈狀肉芽腫", ["血液淋巴癌"]), ("sezary", ["血液淋巴癌"]), ("sézary", ["血液淋巴癌"]),
    ("皮膚t細胞淋巴瘤", ["血液淋巴癌"]), ("多發性骨髓瘤", ["血液淋巴癌"]), ("骨髓瘤", ["血液淋巴癌"]),
    ("白血病", ["血液淋巴癌"]), ("淋巴瘤", ["血液淋巴癌"]),
    ("何杰金", ["血液淋巴癌"]), ("骨髓化生不良", ["血液淋巴癌"]),
    ("骨髓纖維化", ["血液淋巴癌"]), ("紅血球增多", ["血液淋巴癌"]),
    ("血小板增多", ["血液淋巴癌"]), (r"re:漿細胞(?:瘤|性白血病)", ["血液淋巴癌"]),
    ("cml", ["血液淋巴癌"]), ("aml", ["血液淋巴癌"]), ("mds", ["血液淋巴癌"]),
    ("dlbcl", ["血液淋巴癌"]), ("myeloma", ["血液淋巴癌"]),
    ("lymphoma", ["血液淋巴癌"]), ("leukemia", ["血液淋巴癌"]),
    ("惡性黑色素癌", ["其他癌"]), ("黑色素瘤", ["其他癌"]), ("melanoma", ["其他癌"]),
    ("默克細胞癌", ["其他癌"]), ("merkel", ["其他癌"]),
    ("惡性肋膜間皮瘤", ["其他癌"]), ("間皮瘤", ["其他癌"]), ("mesothelioma", ["其他癌"]),
    ("胃腸道基質瘤", ["其他癌"]), ("胃腸基質瘤", ["其他癌"]), ("gist", ["其他癌"]),
    ("軟組織肉瘤", ["其他癌"]), ("脂肪肉瘤", ["其他癌"]), ("纖維肉瘤", ["其他癌"]),
    ("卡波西氏肉瘤", ["其他癌"]), ("肉瘤", ["其他癌"]), ("sarcoma", ["其他癌"]),
    ("kaposi", ["其他癌"]),
    ("神經膠質瘤", ["其他癌"]), ("神經膠母細胞瘤", ["其他癌"]), ("星狀細胞瘤", ["其他癌"]),
    ("神經內分泌", ["其他癌"]), ("甲狀腺癌", ["其他癌"]), ("骨癌", ["其他癌"]),
    (r"re:胸腺(?:癌|瘤)", ["其他癌"]),
    ("腎血管肌脂肪瘤", ["其他癌"]), ("結節性硬化症", ["其他癌"]),
]
DISEASES.sort(key=lambda x: -len(x[0]))
DISEASE_RULES = [(n, re.compile(n[3:]) if n.startswith("re:") else None, cs)
                 for n, cs in DISEASES]

# 器官字樣但非該器官癌別的例外，比對前先消耗掉
EXCLUDE = ["乳房外paget", "extramammarypaget", "乳房攝影", "腎功能", "肝功能",
           "肺功能", "心肺", "肝腎功能", "胃腸道不適", "肺纖維化"]

# 「不含X」「除X以外」「排除X」內的病名不是適應症（坑 #39）
NEG = [re.compile(r"[（(]?不含[^）)，。；]{0,40}[）)]?"),
       re.compile(r"[（(]?除[^）)，。；]{0,40}(?:以外|之外|外)[）)]?"),
       re.compile(r"排除[^，。；]{0,30}")]

# A 級：無視條文內癌名，一律通用（行政共通規則）
UNIVERSAL_A = [
    "使用條件", "登錄", "需經事前審查", "須經事前審查", "經事前審查核准", "需經審查",
    "每次申請", "初次申請", "再次申請", "申請時", "申請續用", "首次申請",
    "病歷", "療效評估", "用藥後", "給付時程", "每日最大劑量", "限每日", "每日至多",
    "每日限處方", "總療程", "治療期間", "停藥", "前述", "本類藥品不得", "本藥品不得",
    "本成分", "疾病診斷或追蹤",
    "每位病人", "每一病人", "同一病人", "病人之", "病人身體狀況", "病患目前", "病人先前",
    "使用本藥", "共通", "給付規定",
]
# B 級：條文內「沒有任何癌名」時才算通用
UNIVERSAL_B = [
    "本類藥品", "本藥品", "本品", "倘", "若病人", "需檢附", "需檢送", "應檢附",
    "必須檢附", "限用於", "適用於", "不得", "每3個月", "每12週", "每24週",
]


def _prep(s):
    t = re.sub(r"\s+", "", unicodedata.normalize("NFKC", s or "")).lower()
    for rx in NEG:
        t = rx.sub("◆", t)
    for e in EXCLUDE:
        t = t.replace(e, "◆")
    return t


def scan_diseases(text):
    """回傳 (癌別 set, 命中的病名 list)"""
    t = _prep(text)
    hits, cancers = [], set()
    for name, rx, cs in DISEASE_RULES:
        if rx is not None:
            m = rx.search(t)
            if m:
                hits.append(m.group(0)); cancers.update(cs); t = rx.sub("◆", t)
        elif name in t:
            hits.append(name); cancers.update(cs); t = t.replace(name, "◆")
    return cancers, hits


def _lead(text):
    t = re.sub(r"\s+", "", text or "")
    t = re.sub(r"^[（(]?[0-9０-９ⅠⅡⅢⅣⅤIVX]+[.．、)）]?", "", t)
    return t[:16]


def classify(text):
    """回傳 (tags, source, rule)"""
    if not re.sub(r"\s+", "", text or ""):
        return ["*"], "fallback-unclassified", []
    ld = _lead(text)
    for k in UNIVERSAL_A:
        if ld.startswith(k):
            return ["*"], "universal-rule", [k]
    cancers, hits = scan_diseases(text)
    if cancers:
        return [c for c in CANCERS if c in cancers], "text-rule", hits
    for k in UNIVERSAL_B:
        if ld.startswith(k):
            return ["*"], "universal-rule", [k]
    return ["*"], "fallback-unclassified", []


def derive_for_drug(d, is_marker):
    """回傳 {(item_idx, sub_idx or None): (tags, source, rule)}"""
    out = {}
    for ii, it in enumerate(d.get("items", [])):
        subs = it.get("subitems", [])
        if is_marker(it):
            out[(ii, None)] = (["*"], "universal-structural", [])
            for si in range(len(subs)):
                out[(ii, si)] = (["*"], "inherit-parent-indication", [])
            continue
        tags, src, rule = classify(it.get("header") or "")
        if src == "text-rule":
            # 標題指明癌別 -> 子項是它的附帶條件
            out[(ii, None)] = (tags, src, rule)
            for si in range(len(subs)):
                out[(ii, si)] = (["*"], "inherit-parent-indication", [])
        else:
            # 傘狀/行政條文 -> 整條顯示，篩選交給子項
            out[(ii, None)] = (["*"], src, rule)
            for si, s in enumerate(subs):
                out[(ii, si)] = classify(s.get("text") or "")
    return out


def cancers_from_tags(d):
    """藥物層 cancers = 全部後代非 * 標籤的聯集"""
    u = set()
    for it in d.get("items", []):
        u.update(x for x in (it.get("cancerTags") or []) if x != "*")
        for s in it.get("subitems", []):
            u.update(x for x in (s.get("cancerTags") or []) if x != "*")
    return [c for c in CANCERS if c in u]
