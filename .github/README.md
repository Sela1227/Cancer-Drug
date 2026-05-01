# GitHub Actions 自動化說明

## check-nhi-update.yml — 健保署資料更新檢測

**執行頻率**：每週一台灣時間 08:00 自動執行（也可手動觸發）

## 檢測策略（多重備援）

健保署網站擋自動化爬蟲非常嚴格（包括擋 GitHub Actions IP），所以採取多重備援，依序嘗試直到成功：

1. **直連 + Chrome UA** — 第一線嘗試
2. **直連 + Safari UA** — 換 UA 再試
3. **r.jina.ai 代理** — 把網頁轉成 markdown 的免費代理服務（最常用的備援）
4. **Google Cache** — 鏡像
5. **Wayback Machine** — Internet Archive 鏡像

任何一個策略成功抓到日期就停止。

## 抓到日期後

從文字內容用 regex 抓:
- `第九節 抗癌瘤藥物 (115.4.23 更新)` → 主要來源
- `chap9_1150423.pdf` → 從 PDF 檔名推回日期

與 `check_nhi.py` 中的 `CURRENT_DATA_DATE` 比對:
- 不一樣 → 自動建 GitHub Issue（labels: `nhi-update`）
- 一樣 → 安靜結束
- 全部失敗 → 建另一個 issue（labels: `check-failed`）

## 設定步驟

### 1. 啟用 Actions

GitHub Repo → Settings → Actions → General → "Allow all actions and reusable workflows"

### 2. 啟用 Issues 寫入權限 ⚠️ 重要

Settings → Actions → General → Workflow permissions → 選 "Read and write permissions"

### 3. 手動測試

Actions tab → 點 "健保署資料更新檢查" → "Run workflow"

## 收到更新通知後的處理

### 步驟（給 Sela）

1. 到 https://www.nhi.gov.tw/ch/cp-7593-ad2a9-3397-1.html 下載新版 PDF
2. 跟 Claude 說「健保署有新版了，請重新整理資料」並上傳 PDF
3. Claude 重跑：
   - PDF 解析 → 145+ 個藥物項目
   - 自動逐癌切片
   - 9.69 等手工切片更新
   - cancer_keywords 字典是否需新增關鍵字
4. 收到新 `Cancer Drug V3.X.zip` 後用 Git Pusher 重打包
5. **改 `.github/scripts/check_nhi.py` 中 `CURRENT_DATA_DATE`** 為新版日期 ⚠️ 不改的話下週又會通知
6. push 後關閉 issue

