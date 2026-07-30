<div align="center">
  <img src="favicon/sela.svg" width="120" alt="SELA"/>
  <h1>健保癌症藥物速查系統</h1>
  <p>查詢健保署藥品給付規定第九節抗癌瘤藥物，選癌別只看相關條文。</p>
</div>

---

## 簡介

給彰濱秀傳癌症中心個管師使用的單檔 HTML 工具，查詢健保署「藥品給付規定第 9 節—抗癌瘤藥物」。核心價值是**依癌別篩選條文**：選定癌別後只顯示該癌別相關的給付條件，避免在 24,000+ 字的長條文（如 9.69 免疫檢查點抑制劑）中迷路。

- 151 個藥物項目；每一條給付條文（含子條文）都帶癌別標籤，通用條件標記為「通用」、任何癌別都會顯示
- 篩選直接作用在健保署原文上（不另存癌別切片），標籤由原文自動推導並有建置端驗證把關，確保**不會有條文被篩掉卻沒人發現**
- 密碼欄可切換遮蔽／顯示
- 內建 139 個藥物的衛教資料庫（機轉、副作用、監測、警示徵兆、生活指導、個管師衛教重點）
- GitHub Actions 每週自動偵測健保署是否更新，有更新自動下載 PDF + 開 Issue + 寄 Email
- 沒有 build process、沒有依賴、沒有後端 — 就一個 `index.html`

資料來源：健保署 115 年 7 月 23 日公告（115 年 8 月 1 日生效）版本。

## 使用

佈署於 GitHub Pages（public repo，前面掛一個防君子的密碼閘）。瀏覽器開啟網址 → 輸入密碼 → 選癌別 / 藥物類別 / 搜尋。

本機亦可直接以瀏覽器開啟 `index.html`（純前端，`file://` 也能跑）。

## 目錄結構

```
健保癌症藥物速查系統/
├── index.html                          單檔主應用（含資料、樣式、邏輯）
├── CLAUDE.md                           專案規則 + 踩過的坑（給下次 Claude）
├── SELA-handoff.md                     給 Kit Claude（升 Kit 用）
├── README.md                           本檔
├── .gitignore                          Git 忽略清單
├── favicon/                            SELA logo / favicon 套件
└── .github/
    ├── README.md
    ├── workflows/check-nhi-update.yml  每週狙擊健保署網站
    └── scripts/check_nhi.py            抓網頁 + 下載 PDF
```

## 版本

V5.1.0 — cancerTags 全庫從原文重推 + 原文內容修復 + 建置端驗證。採 SELA Kit 嚴格三位版號（`V<a>.<b>.<c>`，每位 0–9、逢十進位）。詳見 `CLAUDE.md` 版本歷程。

---

> Made by **SELA** · V5.1.0
