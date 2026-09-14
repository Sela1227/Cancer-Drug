# 未來更新流程設計（給 Claude 接力用）

> 當 Sela 上傳新版健保署 PDF（只含第九節）時，Claude 應該怎麼處理？

## 關鍵差異：跟 V1.0 全新建立 vs 之後的小更新

| 階段 | 工作量 | Claude 做什麼 |
|------|-------|--------------|
| **V1.0 全新建立** | 8 小時 | 從 410 頁 PDF 提取 + 設計 UI + 切片邏輯 + 9.69 手工資料 |
| **小更新 (V3.X+1)** | 30-60 分鐘 | 比對舊版差異 → 增/改藥物資料 → 重打包 |

## 小更新時 Claude 的工作流程

### Step 1: 接收新 PDF (Sela 上傳)

Sela 會說類似：
> 健保署 115.7.23 有新版了，這是新的第九節 PDF

只給第九節 PDF（不再是整本 410 頁）。

### Step 2: 解析新 PDF（同樣的腳本）

用之前的腳本流程：
1. `pdftotext -layout` 把 PDF 轉文字
2. 用 `extract_v5.py` 同樣的邏輯解析 145+ 個藥物
3. 產生新版 `drugs_final.json`

**關鍵**：因為只有第九節，不需要找章節範圍，直接整個 PDF 當作第九節處理。需確認：
- 是否有新增藥物（如 9.135、9.136...）
- 是否有刪除藥物
- 是否有條文修改

### Step 3: 比對新舊資料 (DIFF 報告)

寫一個 `compare_versions.py`：
```python
# 對照 drugs_final.json (舊) vs drugs_final_new.json (新)
# 產生 DIFF 報告：
# - 新增藥物：9.135 XXX
# - 刪除藥物：(無 / 9.X)
# - 條文修改：9.69 第 2 條 (7) 段 早期三陰性乳癌 ← 內容變化標出
# - 適應症新增癌別：9.X 從 [乳癌] → [乳癌, 肝膽胰胃癌]
```

把 DIFF 報告交給 Sela 確認，避免漏看健保署新增/修改的內容。

### Step 4: 處理 9.69 等手工切片

如果 DIFF 顯示 9.69 內容變了：
- 對照新版 9.69 條文，更新 `per_cancer_data.py` 的 `ICI_BY_CANCER`
- 特別注意 PD-L1 表格是否變動 (新增癌別、新增製劑、門檻變化)
- 新增的免疫藥物可能要加進手工切片清單

### Step 5: 處理新增的跨癌藥物

新增的藥物如果跨多癌別：
- 自動切片邏輯會處理（Cancer Drug V3.3 已建立）
- 抽樣驗證 1-2 個確認分類正確

### Step 6: 重生成 index.html

跑 `make_html_v6.py` (邏輯不變，只是用新的 drugs_final.json)。

### Step 7: 更新版本號和資料截止日

需要改的地方：
1. `index.html` 內 `<span class="brand-version">v3.4.2</span>` → 新版本號
2. `index.html` 內 `<span class="brand-data-date">資料截止 115/4/23</span>` → 新日期
3. `.github/scripts/check_nhi.py` 中 `CURRENT_DATA_DATE = "115.4.23"` → 新日期
4. CLAUDE.md 版本歷程加新行
5. 如有新坑，CLAUDE.md 第三章編號累積

### Step 8: 打包 Cancer Drug V3.X+1.zip

完整 zip 含 index.html + CLAUDE.md + .github/

### Step 9: 給 Sela

Sela 用自動部署工具推送，關閉 GitHub Issue。

## Claude 在處理小更新時要注意

1. **不要重做 UI**: HTML/CSS 結構保持不變，只改資料部分
2. **不要重做 9.69 全部手工資料**: 只改變動的部分
3. **保留所有踩過的坑**: 編號累積，新坑加在後面
4. **產出 DIFF 報告**: 讓 Sela 知道哪些藥變了
5. **驗證**: 跑煙霧測試確認沒壞

## Claude 如果遇到的特殊情況

### A. 健保署新增章節結構（如新增第 9.X+1 大類藥）
- 檢查 PDF 解析 regex 是否仍適用
- 加新藥到 cancer_keywords 字典

### B. 健保署修改 PDF 格式
- 例如改用不同表格、改縮排
- 可能需要更新 `parse_clauses` 邏輯
- **記錄成新坑**

### C. 9.69 PD-L1 表格大改
- 手工重整 `per_cancer_data.py` 的 pdl1 文字
- 可能要花較多時間

## 關鍵：Claude 怎麼知道目前用什麼版本？

**從 CLAUDE.md 的「版本歷程」直接看**:
```
| 版本 | 重點 |
|------|------|
| V3.4.2 | 自動下載 PDF + Issue 通知 |
```

Sela 上傳新 PDF 時 Claude 應該：
1. 先讀 CLAUDE.md（如果 project knowledge 有）
2. 確認當前版本（最後一行 V3.4.2）
3. 產生新版 V3.4.3 或 V3.5（依改動程度）
