# tools/ — 建置與驗證腳本

這些腳本**不會被部署**，但它們是「如何安全更新這份資料」的一部分。
判斷檔案該不該進 repo，不是問「它是不是部署產物」，
而是問「**沒有它，別人能不能安全地改這個專案**」（CLAUDE.md 坑 #58）。

## 更新健保署條文的標準流程

```bash
# 0. 先做兩層 diff，確認變動範圍（條號層 → 內容層）
#    新檔放在 /mnt/project/chap9_<日期>.pdf（副檔名是 pdf，內容其實是純文字）

# 1. 改資料（依當次變動另寫一支 update_<日期>.py，逐字取自官方原文）
python3 tools/update_<日期>.py index.html /mnt/project/chap9_<日期>.pdf

# 2. 閘門：BLOCK 必須為 0 才可出版
python3 tools/validate.py index.html /mnt/project/chap9_<日期>.pdf

# 3. 事審 × 癌別盤點：與上版比對，分歧藥增減要能解釋
python3 tools/pa_matrix.py index.html

# 4. 需要溯源稽核檔時
python3 tools/rederive.py index.html --write
```

## 各腳本職責

| 檔案 | 做什麼 | 失敗代表什麼 |
|---|---|---|
| `lib_drugs.py` | 共用底層：載入/寫回 drugs、原文分節、正規化、`search_text` 重生 | — |
| `derive_tags.py` | **癌別標籤怎麼來的唯一真相**。要調整就改這裡再重跑，不手改資料 | — |
| `diff_source.py` | 機械式全文差異回歸（雙向） | 漏抄 / 錯字 / 條號沒收錄 |
| `rederive.py` | 出版檔標籤 vs 規則重推 | 有人繞過推導規則手改了資料 |
| `pa_matrix.py` | 事前審查 × 癌別交叉盤點 | （不 exit 1，供人工比對）|
| `validate.py` | 合規閘門，並自動委派上面兩支 | **BLOCK ≥1 就不得出版** |

## 兩條紀律

1. **重建或修改工具後，先在「舊資料 + 舊原文」上跑一次**，確認重現原結果，才拿去驗新資料。
   重建的工具要先證明自己等價。
2. **`diff_source.py` 的價值不在第一次跑出多少筆**，而在能不能把誤報壓到 0。
   壓到 0 之後，任何一筆新出現的差異都是真的。

## 產物（已列入 .gitignore）

`report_validate.txt`／`report_fulldiff.txt`／`report_rederive.txt`／`report_pa_matrix.txt`／
`report_update.txt`／`drugs_audit.json`
