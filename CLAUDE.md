# CLAUDE.md — 健保癌症藥物速查系統

> 給下次接手這專案的 Claude。讀完這份能直接動手，不需要從頭問。

---

## 一、這是什麼

單檔 HTML 工具,給彰濱秀傳癌症中心的個管師(Sela 等 3 人)查健保署藥品給付規定第 9 節抗癌瘤藥物。資料源是健保署 115 年 4 月 23 日更新的 PDF。佈署在 GitHub Pages public repo,前面掛了一個防君子的密碼閘。

整個專案就一個 HTML 檔加上 GitHub Actions:
- `index.html`(約 840 KB)
- `.github/workflows/check-nhi-update.yml` + `.github/scripts/check_nhi.py`:每週狙擊健保署網站,有更新自動下載 PDF + 開 Issue + 寄 email

**沒有 build process、沒有依賴、沒有後端**。

**核心臨床價值**:選擇癌別後只看到該癌別相關條件,避免在 24,000+ 字長條文(如 9.69)中迷路。33 個跨癌藥物 100% 完成逐癌切片。

---

## 二、單一真相對映表

| 設定項 | 位置 | 改的時候要對齊什麼 |
|--------|------|------|
| 密碼 | `index.html` 內 `PASSWORD_HASH` | `echo -n "新密碼" \| sha256sum` |
| 主色 | `:root --primary: #436f8a` | 連帶改:`theme-color`、入口頁/body 漸層、FAB shadow、search shadow |
| 藥物資料 | `index.html` 內 `const drugs = [...]` | 145 個藥物 |
| 9.69 手工資料 | `per_cancer_data.py` → `per_cancer_data.json` | 9.69 因含 PD-L1 表格,需手工逐癌 |
| 自動切片邏輯 | `make_html_v6.py` 的 `cancer_keywords` | 加新癌別關鍵字時要更新 |
| **資料當前版本** | `.github/scripts/check_nhi.py` 的 `CURRENT_DATA_DATE` | **每次重建資料時更新成新的 YY.M.D** ⚠️ |
| Logo | `data:image/jpeg;base64,...` | 三處引用同一變數 |

---

## 三、踩過的坑（編號累積，永不重排）

1. **檔名用中文 → GitHub Pages URL 變編碼地獄**  → 永遠用 `index.html`

2. **PDF 章節標題前面有空格 → regex 抓不到**  → regex 改成 `^\s{0,3}9\.\d+\.`

3. **SubtleCrypto 在 file:// 不可用**  → 純 JS SHA-256 fallback

4. **藥物父項目自己沒有適應症內文**  → V3.3 父項目展開時把子項目內容合併呈現,並做精細逐癌切片

5. **多個 sticky 元素 z-index 競爭**  → filter-panel: 300、filter-overlay: 250、topbar: 200

6. **桌機 close button 被一起隱藏**  → 用 ID 限定 `#filter-panel .close-btn`

7. **PDF 條文裡有日期戳干擾**  → regex `\s*[（(][\d/、]+[）)]` 全部移除

8. **藥物分類有交集**  → types 是 array

9. **【V3.1】用截斷字數處理長條文**  → 改用結構化解析 + 逐癌切片

10. **【V3.1】主編號判斷需驗證連續編號**  → 用 `next_main_num`,不靠縮排

11. **【V3.1】1280px 寬螢幕版面失調**  → max-width 改 1400px

12. **【V3.2】跨癌藥物即使結構化展開仍混亂**  → 選癌別時只渲染該癌別卡片

13. **【V3.2】PDF 表格被切成條狀資料**  → 9.69 手工整理成文字描述

14. **【V3.2】Header 雙色配色視覺亂**  → 改純單色

15. **【V3.3】is_empty_parent 判斷錯誤**  → 改用「有沒有編號條文 1.」判斷

16. **【V3.3】父項目逐癌切片粗暴歸類**  → 對父項目合併後的每個 clause 再做一次精細匹配

17. **【V3.3】空父項目展開時無內容**  → 加入「父分類提示卡」+ 來源標記

18. **【V3.4】健保署網站擋台灣 IP 爬蟲(包括 GitHub Actions IP)**
    - 症狀:容器 + GitHub Actions runner 4 個 UA 全部 HTTP 403
    - 做法:**多重備援策略**(直連 + r.jina.ai + Google Cache + Wayback Machine)
    - 實測 2026/5/1:GitHub Actions 第二次手動 trigger 時直連成功 (HTTP 200,117KB),猜測健保署擋人有時間/隨機性
    - 重要結論:即使第一次成功,後備策略仍要保留(下次可能換 IP 就被擋)

19. **【V3.5】要自動下載 PDF 給人類重做**
    - 需求:Issue 通知時直接附 PDF 下載連結
    - 限制:GitHub Actions API 建 Issue 時無法直接附檔
    - 做法:把 PDF 上傳為 artifact (90 天保留),Issue body 內貼 artifact 下載連結
    - PDF URL 抓取:從第九節到第十節之間找 `chap9_NNNNNNN.pdf` 或 `dl-XXXXX-...pdf` 連結
    - 抓不到時會在 Issue 內提供原始健保署連結讓人手動下載

---

20. **【V3.5】Header 顯示版本號和資料截止日**
    - 需求:Sela 想知道目前看的是哪個版本、資料是哪天的
    - 做法:topbar 加 `<span class="brand-version">v3.5</span>` 和 `<span class="brand-data-date">資料截止 115/4/23</span>`
    - 手機版 (≤768px) 把資料截止日獨立成第二行避免擠
    - 超小螢幕 (≤380px) 隱藏版本號

21. **【V3.5】小更新時 Claude 接力的處理流程**
    - 需求:之後 Sela 只會給第九節 PDF (不再是整本 410 頁),Claude 怎麼快速處理
    - 做法:寫了 `.github/未來更新流程設計.md` 詳細列出 9 步驟
    - 關鍵:不要重做 UI,只改資料;產出 DIFF 報告讓 Sela 確認

## 四、版本歷程

| 版本 | 重點 |
|------|------|
| V3.0 | 漸層背景、玻璃毛霧 sticky header |
| V3.1 | 結構化條文呈現、長條文不截斷 |
| V3.2 | 逐癌切片(9.69 手工 + 28 自動) |
| V3.3 | 父項目從子合併 + 精細逐癌切片 (33 個跨癌藥 100% 切片) |
| V3.4 | GitHub Actions 自動檢測健保署資料更新 |
| V3.4.1 | 加多重備援策略 (r.jina.ai 等) |
| V3.4.2 | 偵測到更新時自動下載 PDF**,上傳為 artifact,Issue 直接附下載連結 |

---

## 五、關鍵路徑

```
專案結構:
├── index.html                              # 單檔主應用
├── CLAUDE.md                               # 本文件
└── .github/
    ├── README.md
    ├── workflows/check-nhi-update.yml      # 每週狙擊
    └── scripts/check_nhi.py                # 抓網頁 + 下載 PDF

開發端 (產生 index.html 用,不放 repo):
├── drugs_final.json                        # 145 個藥物原始解析
├── per_cancer_data.py / .json              # 9.69 手工資料
├── make_html_v6.py                         # 產生 drug_data
└── logo_b64.txt                            # SELA logo
```

---

## 六、佈署流程

### 6.1 一般版本更新
1. 改完 index.html 後本機測試
2. Git Pusher 打包 `Cancer Drug V3.X.zip`
3. 用 Sela 的自動部署工具推送

### 6.2 收到「健保署有新版」issue 時 (核心使用流程!)
1. **點 Issue 內 "前往下載" 連結** → Actions run 頁面 → 底下 Artifacts → 下載 `chap9-pdf-XXX.zip` → 解壓得 PDF
2. 開新 Claude 對話「健保署有新版了,請重新整理資料」+ 上傳 PDF
3. Claude 重做後得到新 `Cancer Drug V3.X.zip`
4. Git Pusher 推送
5. **改 `.github/scripts/check_nhi.py` 中 `CURRENT_DATA_DATE`** 為新日期 ⚠️
6. 關閉 GitHub Issue

如果 PDF 自動下載失敗,Issue 內會有原始健保署連結讓你手動下載。

---

## 七、Claude 重做資料時的處理重點

當 Sela 上傳新版 PDF 並說「健保署有新版了」,Claude 接手要做：

1. **重跑 PDF 解析** → 145+ 個藥物項目 (新版可能有新增藥物 9.135、9.136...)
2. **驗證自動切片**:跑 cancer_keywords 字典看新藥能否正確分類
3. **檢查 9.69 手工資料**:免疫檢查點抑制劑常變動,要對照新版的條文重整 ICI_BY_CANCER (per_cancer_data.py)
4. **檢查新增的條文中是否有跨癌藥物**:如有,加入手工切片或自動切片清單
5. **更新 CLAUDE.md**:版本歷程加新行、踩過的坑加新編號(如有新坑)
6. **打包成新版 Zip**:Cancer Drug V3.5.zip

---

## 八、下版候選工作

按優先序：

1. **驗證自動切片正確性** — 32 個自動切片的藥物建議由 Sela 抽樣驗證
2. **驗證自動下載 PDF 機制** — 等下次健保署真的有更新時看是否能自動抓到 PDF
3. 加入「複製藥物連結」功能
4. 列印優化:選中的藥物展開後列印只列印展開的那些
5. 加常用清單功能(localStorage)
6. 把 13 癌 59 項品質指標附件整合進來
7. 加入「最近查詢」歷史紀錄

---

## 九、一句話總結

V3.4.2 完成了「**健保署有更新 → 自動下載 PDF → 寄 Email 通知 Sela → 點連結下載 PDF → 給 Claude 重做 → 推送**」的閉環自動化。Sela 完全不用主動查健保署網站,系統永遠跟最新規定同步。下版重點是抽樣驗證自動切片正確性。
