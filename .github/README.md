# GitHub Actions 自動化說明

## check-nhi-update.yml — 健保署資料更新檢測

**執行頻率**：每週一台灣時間 08:00 自動執行（也可手動觸發）

## 運作流程

```
每週一 08:00
   ↓
1. 用 5 種策略嘗試抓健保署網頁
   - 直連 (Chrome UA)
   - 直連 (Safari UA)
   - r.jina.ai 代理
   - Google Cache
   - Wayback Machine
   ↓
2. 找出第九節抗癌瘤藥物的更新日期
   ↓
3. 比對 CURRENT_DATA_DATE
   ↓
   ├── 沒更新 → 安靜結束
   ├── 有更新 → 4. 自動下載 PDF
   │              ↓
   │           5. 上傳 PDF 為 artifact (保留 90 天)
   │              ↓
   │           6. 建立 GitHub Issue (含 PDF 下載連結)
   │              ↓
   │           7. GitHub 自動寄 email 通知 (預設已開)
   │
   └── 全部失敗 → 建立警告 Issue
```

## 收到通知的處理流程

### 1. Email 通知

GitHub 預設會把 Issue 通知寄到你註冊的 email：
- 主旨類似「[Sela1227/cancer-drug] 健保署第九節抗癌瘤藥物有新版（115.7.23）」
- 內文包含 Issue 連結

### 2. 點 Issue 連結

裡面會有：
- 新舊版本日期比對
- **新版 PDF 自動下載連結**（指向 GitHub Actions artifact）
- 健保署原始連結（備援）
- 接手步驟

### 3. 下載 PDF

點 Issue 內的「前往下載」連結 → 進入 Actions run 頁面 → 滑到底找 Artifacts 區 → 下載 `chap9-pdf-XXX.zip` → 解壓得到 PDF

### 4. 給 Claude 重做資料

開新對話：
> 健保署有新版了，請重新整理資料

上傳 PDF。Claude 會重跑解析 → 切片 → 重新打包。

### 5. 推送並更新版本標記

收到新 Zip 後：
1. 用 Git Pusher 推送
2. **改 `.github/scripts/check_nhi.py` 中的 `CURRENT_DATA_DATE`** 為新日期 ⚠️ 重要
3. 關閉 GitHub Issue

## 設定步驟

### 1. 啟用 Actions

GitHub Repo → Settings → Actions → General → "Allow all actions and reusable workflows"

### 2. 啟用 Issues 寫入權限 ⚠️ 重要

Settings → Actions → General → Workflow permissions → 選 "Read and write permissions"

### 3. Email 通知（預設已開，可確認）

Settings → Notifications → Email：
- 確認 "Issues" 那欄勾了 "Email"
- 也確認你的 email 已 verified

## 為什麼 PDF 用 artifact 不直接附在 Issue？

GitHub Issue 雖然支援檔案附件，但 **Actions 用 API 建 Issue 時無法直接附檔**。所以採用：
- **Artifact** 儲存 PDF（90 天有效期）
- **Issue 內容**包含 artifact 下載連結

實務上多按一個連結就到，不算太麻煩。
