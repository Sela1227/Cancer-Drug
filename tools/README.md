# tools/ — 建置與驗證腳本

這些腳本**不會被部署**，但它們是「如何安全更新這份資料」的一部分。
判斷檔案該不該進 repo，不是問「它是不是部署產物」，
而是問「**沒有它，別人能不能安全地改這個專案**」（CLAUDE.md 坑 #58）。

## 來源檔：**PDF ＋ DOCX 兩個都要**（坑 #60）

| 格式 | 給什麼 | 缺什麼 |
|---|---|---|
| **PDF** | **條號層級**（1./(1)/Ⅰ.）—— 唯一完整的 | 跨行截斷、中文字間空白、表格壓平、上標拉平 |
| **DOCX** | **段落邊界、真上標 run、真表格** | Word 自動編號不在 `p.text`（128 處） |
| ODT | — | 條號跟 DOCX 一樣缺、上標跟 PDF 一樣拉平 → **不用給** |

PDF 請用 `pdftotext` 轉成文字檔再用。

## 更新健保署條文的標準流程

```bash
# 0. 兩層 diff 確認變動範圍（條號層 → 內容層）
pdftotext chap9_<日期>.pdf src_<日期>.txt

# 1. 改資料（依當次變動另寫一支 update_<日期>.py）
#    變動 ≤5 條 → 外科手術式 patch；變動多或來源格式有變 → 全庫重建
python3 tools/update_<日期>.py index.html

# 2. 閘門：BLOCK 必須為 0 才可出版（以 DOCX 為基準，表格才對得上）
python3 tools/validate.py index.html chap9_<日期>.docx

# 3. 事審 × 癌別盤點：與上版比對，分歧藥增減要能解釋
python3 tools/pa_matrix.py index.html

# 4. 需要溯源稽核檔時
python3 tools/rederive.py index.html --write
```

## 全庫重建時務必保護的欄位

重建會覆蓋一切，但這些**不可由原文推導**：

- **已刪除條號**（9.7/9.84/9.89）的說明文字是我們寫的，官方只留「（刪除）」
- **父項目**（9.1/9.5/9.12/9.16/9.32/9.36/9.44）的條文來自子項目合併 → 一律由子項目重建
- **新藥的 `types`**（標靶/化療/免疫/荷爾蒙）條文不會講 → 對照同類藥人工指定
- **任何逐字取自原文的字串都不可硬編碼**（表尾註實測被官方改過）

## 各腳本職責

| 檔案 | 做什麼 | 失敗代表什麼 |
|---|---|---|
| `lib_drugs.py` | 共用底層：載入/寫回 drugs、原文分節、正規化、`search_text` 重生；`read_source()` 同時吃 PDF 文字與真 DOCX | — |
| `merge_sources.py` | DOCX 段落（上標還原）、DOCX 真表格、PDF 編號前綴索引 | — |
| `parse_section.py` | 把原文解析成 items/subitems；`parse_docx_sections()` 是主要入口 | — |
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
