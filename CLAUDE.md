# CLAUDE.md — 健保癌症藥物速查系統

> 給下次接手這專案的 Claude。讀完這份能直接動手，不需要從頭問。

---

## 一、這是什麼

單檔 HTML 工具,給彰濱秀傳癌症中心的個管師(Sela 等 3 人)查健保署藥品給付規定第 9 節抗癌瘤藥物。資料源是健保署 115 年 4 月 23 日更新的 PDF。佈署在 GitHub Pages public repo,前面掛了一個防君子的密碼閘。

整個專案就一個 HTML 檔加上 GitHub Actions:
- `index.html`(約 840 KB):145 個藥物資料、SELA logo (base64)、純 JS SHA-256、密碼閘、主應用
- `.github/workflows/check-nhi-update.yml` + `.github/scripts/check_nhi.py`:每週狙擊健保署網站,有更新自動開 Issue

**沒有 build process、沒有依賴、沒有後端**。

**核心臨床價值**:選擇癌別後只看到該癌別相關條件,避免在 24,000+ 字長條文(如 9.69)中迷路。33 個跨癌藥物 100% 完成逐癌切片。

---

## 二、單一真相對映表

| 設定項 | 位置 | 改的時候要對齊什麼 |
|--------|------|------|
| 密碼 | `index.html` 內 `PASSWORD_HASH` | `echo -n "新密碼" \| sha256sum` |
| 主色 | `:root --primary: #436f8a` | 連帶改:`theme-color`、入口頁/body 漸層、FAB shadow、search shadow |
| 藥物資料 | `index.html` 內 `const drugs = [...]` | 145 個藥物。每個含 `items`、`per_cancer`、`is_manual_split`、`is_real_parent_with_children`、`is_parent` |
| 9.69 手工資料 | `per_cancer_data.py` → `per_cancer_data.json` | 9.69 因含 PD-L1 表格,需手工逐癌 |
| 自動切片邏輯 | `make_html_v6.py` 的 `cancer_keywords` | 加新癌別關鍵字時要更新這裡 |
| 父項目處理 | `make_html_v6.py` 的 `is_empty_parent()` | 用「有沒有編號條文 1.」判斷 |
| **資料當前版本** | `.github/scripts/check_nhi.py` 的 `CURRENT_DATA_DATE` | **每次重建資料時更新成新的 YY.M.D** |
| Logo | `data:image/jpeg;base64,...` | 三處引用同一變數 |

---

## 三、踩過的坑（編號累積，永不重排）

1. **檔名用中文 → GitHub Pages URL 變編碼地獄**
   - 做法:repo 裡的檔名永遠是 `index.html`

2. **PDF 章節標題前面有空格 → regex 抓不到**
   - 做法:regex 改成 `^\s{0,3}9\.\d+\.`

3. **SubtleCrypto 在 file:// 不可用**
   - 做法:純 JS SHA-256 fallback (sha256_js)

4. **藥物父項目自己沒有適應症內文**
   - 做法:V3.3 父項目展開時把子項目內容合併呈現,並做精細逐癌切片

5. **多個 sticky 元素 z-index 競爭**
   - filter-panel: 300、filter-overlay: 250、topbar: 200、search-section: 100

6. **桌機 close button 被一起隱藏**
   - 做法:用 ID 限定 `#filter-panel .close-btn`

7. **PDF 條文裡有日期戳干擾**
   - 做法:regex `\s*[（(][\d/、]+[）)]` 全部移除

8. **藥物分類有交集**
   - 做法:types 是 array,搜尋用 `some(t => selectedTypes.has(t))`

9. **【V3.1】用截斷字數處理長條文 → 切掉關鍵癌別資訊**
   - 做法:結構化解析 + V3.2 的逐癌切片

10. **【V3.1】主編號判斷需驗證連續編號**
    - 做法:用 `next_main_num` 連續編號驗證,不靠縮排判斷

11. **【V3.1】1280px 寬螢幕版面比例失調**
    - 做法:max-width 改 1400px、加 `@media (min-width: 1200px)`

12. **【V3.2】跨癌藥物即使結構化展開仍混亂**
    - 做法:選癌別時只渲染該癌別的卡片,沒選時顯示完整原文

13. **【V3.2】PDF 表格被切成條狀資料**
    - 做法:9.69 改用手工整理的 `pdl1: "癌別 (P001):..."` 文字格式

14. **【V3.2】Header 雙色配色視覺亂**
    - 做法:topbar 用 `--primary-darker`,search-section 用 `--primary-dark`

15. **【V3.3】is_empty_parent 判斷錯誤**
    - 症狀:9.5、9.16、9.36 等父項目被誤判為「有自己內文」
    - 原因:第一行有日期戳被算入 body
    - 做法:改用「有沒有編號條文 1.」判斷:`re.search(r"\n\s*1\.\s*\S", d["content"])`

16. **【V3.3】父項目逐癌切片粗暴歸類**
    - 症狀:選乳癌看 9.5 Paclitaxel,出現非小細胞肺癌等不屬於乳癌的條文
    - 做法:改成精細匹配 — 對父項目合併後的每個 clause 再做一次 `classify_text_to_cancer`

17. **【V3.3】Aromatase Inhibitors (9.1) 等空父項目展開時無內容**
    - 做法:加入「父分類提示卡」+「從子項目合併顯示」+「來源標記 `【9.1.1 Exemestane】`」

18. **【V3.4】健保署網站擋台灣 IP 爬蟲**
    - 症狀:從容器或台灣端 IP 抓 https://www.nhi.gov.tw/ch/cp-7593-ad2a9-3397-1.html 都是 403 Forbidden
    - 原因:健保署擋自動化爬蟲(可能擋 UA 也可能擋特定 IP 段)
    - 做法:**用 GitHub Actions** 從美國 IP 出去,通常能通過。並加上多 User-Agent 輪詢、PDF 檔名 fallback regex
    - 備援:如果 GitHub Actions 也被擋,workflow 會建另一個 issue 提醒人工檢查

---

## 四、版本歷程

| 版本 | 重點 |
|------|------|
| V3.0 | 內容頁背景改用漸層、玻璃毛霧 sticky header |
| V3.1 | 結構化條文呈現 + 智能高亮、解決長條文截斷 |
| V3.2 | 逐癌切片(9.69 手工 + 28 個自動)、Header 改純單色 |
| V3.3 | 父項目從子項目合併 + 精細逐癌切片(9.1、9.5、9.12、9.16、9.32、9.36、9.44) |
| V3.4 | **GitHub Actions 自動檢測健保署資料更新**,每週狙擊有更新自動開 Issue |

---

## 五、關鍵路徑

```
專案結構:
.
├── index.html                              # 單檔主應用
├── CLAUDE.md                               # 本文件
└── .github/
    ├── README.md                           # GitHub Actions 機制說明
    ├── workflows/
    │   └── check-nhi-update.yml            # 每週狙擊 workflow
    └── scripts/
        └── check_nhi.py                    # 抓健保署網站的 Python 腳本

開發端 (產生 index.html 時用的腳本,不放在 repo):
├── drugs_final.json                        # 145 個藥物原始解析資料
├── per_cancer_data.py / .json              # 9.69 手工逐癌資料
├── make_html_v6.py                         # 產生 drug_data 的腳本
└── logo_b64.txt                            # SELA logo base64

index.html 內部結構:
<style>
  :root                               # 主色階變數
  body                                # 背景漸層
  .topbar / .search-section           # 純單色 header
  .filter-panel / #info-panel         # 滑出面板
  .drug / .drug-body                  # 藥物卡片
  .cancer-card                        # 逐癌切片獨立卡
  .pdl1-block                         # PD-L1 文字描述
  .common-conditions                  # 通用條件區
  .source-marker                      # 來源標記【9.1.1 Exemestane】
  .parent-notice                      # 父分類提示
  .clause / .subitem                  # 完整原文(沒選癌別時)
  .pill / .tag / .chip                # 篩選元件

<script>
  drugs = [...]                       # 145 個藥物
  renderManualCancerCard()            # 9.69 手工切片渲染
  renderAutoCancerCard()              # 自動切片渲染
  renderFullClauses()                 # 原文渲染
  PASSWORD_HASH                       # SHA-256 of "Sela"
```

---

## 六、煙霧測試

### 6.1 主應用測試
```bash
python3 -m http.server 8000
# 開瀏覽器 → 輸入密碼 Sela
# 檢查項目:
#   [ ] 主畫面 145 個藥物
#   [ ] 桌機看得到左側篩選欄、手機要點按鈕
#   [ ] 選乳癌:乳癌 tag 變藍底白字(不跳選)、其他 tag 灰
#   [ ] 展開 9.69 → 只看到「乳癌 — 早期三陰性乳癌」獨立卡(含 PD-L1)
#   [ ] 展開 9.5 (父項目) → 顯示「父分類:9.5.1、9.5.2」+ 各子的條文
#   [ ] 選乳癌後 9.5 → 只看到 9.5.1 中乳癌相關條文
#   [ ] 展開 9.1 Aromatase Inhibitors → 看到 9.1.1、9.1.2、9.1.3
#   [ ] 選婦癌看 9.16 → 只看到卵巢/子宮頸癌相關
#   [ ] 選泌尿癌看 9.36 → 只看到腎細胞癌相關
#   [ ] 搜尋 EGFR 找到 16 個藥物
#   [ ] 列印鈕產生純白底列印預覽
```

### 6.2 GitHub Actions 測試
首次部署到 GitHub Pages 後:
1. 到 Actions tab → 點 "健保署資料更新檢查"
2. 點 "Run workflow" → 觀察是否能 HTTP 200 抓到網頁
3. 預期 log 顯示:「✓ 沒有更新 (皆為 115.4.23)」

如果出現「❌ 所有嘗試失敗」:
- 看是 HTTP 403 (健保署擋) 還是其他錯誤
- 嘗試手動修改 `.github/scripts/check_nhi.py` 的 USER_AGENTS 或 headers

---

## 七、佈署流程

### 7.1 首次佈署
```
1. GitHub 開新 repo (建議名 sela-cancer-drug-query, public)
2. 把整包 V3.X 解壓上傳 (含 index.html、CLAUDE.md、.github/)
3. Settings → Pages → Source: main / (root) → Save
4. Settings → Actions → General → Workflow permissions: Read and write
5. 1-2 分鐘後 https://<account>.github.io/<repo>/ 生效
6. 進 Actions tab 手動跑一次 "健保署資料更新檢查",確認 OK
7. 把網址 + 密碼「Sela」分享給其他個管師
```

### 7.2 一般版本更新
```
1. 改完 index.html 後本機測試
2. Git Pusher 打包 Zip:「健保癌症藥物速查系統 V3.X.zip」
3. 自動 push main branch
4. GitHub Pages 1-2 分鐘後生效
```

### 7.3 收到健保署更新 issue 時
```
1. 到健保署下載新版 PDF
2. 開 Claude 說「健保署有新版了,請重新整理資料」上傳 PDF
3. Claude 重跑:PDF 解析 → 自動切片 → 9.69 等手工切片更新
4. 收到新 Zip 後用 Git Pusher 打包
5. 改 .github/scripts/check_nhi.py 中的 CURRENT_DATA_DATE 為新日期 ⚠️ 重要!
6. push 後關閉 GitHub issue
```

---

## 八、升版指引

每次升版要更新:
1. CLAUDE.md 踩過的坑加新編號(如有新坑)
2. 版本歷程加一行
3. 下版候選工作重排
4. **如果是健保署資料更新**:還要改 `check_nhi.py` 的 `CURRENT_DATA_DATE`(否則自動檢測會永遠以為有新版)

**改逐癌資料時**:
- 加新藥到手工切片:在 `per_cancer_data.py` 的 `ICI_BY_CANCER` 加新項目
- 自動切片有問題:檢查 `cancer_keywords` 字典是否漏了關鍵字
- 父項目處理:看 `is_empty_parent` 與 `has_children` 是否判斷正確

---

## 九、下版候選工作

按優先序：

1. **驗證自動切片正確性** — 32 個自動切片的藥物建議由 Sela 抽樣驗證,有錯的個案加到手工版
2. **驗證 GitHub Actions 真的能抓到網頁** — 部署後到 Actions tab 手動跑一次,看是否 HTTP 403。若失敗要設計備援(例如改用 RSS、Wayback Machine 鏡像、或第三方 mirror)
3. 加入「複製藥物連結」功能(產生帶 hash 的 URL)
4. 列印優化:選中的藥物展開後列印只列印展開的那些
5. 加常用清單功能(個管師可標記常用藥物,localStorage)
6. 把 13 癌 59 項品質指標附件整合進來
7. 加入「最近查詢」歷史紀錄

第 1、2 名是上線前必驗:臨床正確性 + 自動化機制可運作。

---

## 十、一句話總結

V3.4 加上 GitHub Actions 每週狙擊健保署網站,有更新自動開 Issue 通知 — 解決「個管師可能不知道規定改了」的最大臨床風險。資料、UI、佈署、自動化監控全部到位。下版重點是抽樣驗證自動切片正確性。

**未來健保署規則更新流程**:
```
GitHub Actions 偵測到 → 自動開 Issue → 個管師看到通知
→ 找 Claude 重建資料 → Git Pusher 重打包 → push 自動部署
```
個管師完全不用主動查健保署網站,系統永遠跟最新規定同步。
