# GitHub Actions 自動化說明

## check-nhi-update.yml — 健保署資料更新檢測

**執行頻率**：每週一台灣時間 08:00 自動執行（也可手動觸發）

**運作邏輯**：
1. 抓取健保署「最新版藥品給付規定」頁面
2. 用 regex 抓「第九節 抗癌瘤藥物 (YY.M.D 更新)」的日期
3. 與系統內 `CURRENT_DATA_DATE` 比對

**有更新時**：自動建立 GitHub Issue（labels: `nhi-update`），通知您手動重建資料

**檢測失敗時**：自動建立另一個 Issue（labels: `check-failed`），請手動到健保署檢查

## 設定步驟

### 1. 啟用 Actions（首次部署時）

GitHub Repo → Settings → Actions → General → 確認 "Allow all actions and reusable workflows" 已勾選。

### 2. 啟用 Issues 寫入權限

Settings → Actions → General → Workflow permissions → 選 "Read and write permissions"，確認 "Allow GitHub Actions to create and approve pull requests" 勾選（雖然這個 workflow 用 issue 不用 PR，但保險起見）。

### 3. 手動測試一次

到 Actions tab → 點 "健保署資料更新檢查" → "Run workflow" → 觀察 log 確認能正確抓到日期。

## 收到更新通知後的處理

### Issue 標題範例

> 健保署第九節抗癌瘤藥物有新版（115.7.23）

### 處理步驟（給 Sela）

1. 到 https://www.nhi.gov.tw/ch/cp-7593-ad2a9-3397-1.html 下載新版 PDF
2. 開新對話跟 Claude 說「健保署有新版了，請重新整理資料」並上傳 PDF
3. Claude 會重跑：
   - PDF 解析 → 145+ 個藥物項目
   - 自動逐癌切片
   - 9.69 等手工切片更新
4. 收到新的 `健保癌症藥物速查系統 V3.X.zip` 後用 Git Pusher 重打包
5. 更新 `.github/scripts/check_nhi.py` 中的 `CURRENT_DATA_DATE` 為新版日期
6. push 後關閉 issue

### 重要：怎麼確認新版有納入哪些變動

健保署也會發布「修訂對照表」(自 YY 年 M 月 D 日生效)，顯示新增/修改的條文。如果只是改幾個藥，您可以直接告訴 Claude「只有 9.X 改了」，這樣就不用整個重做。

