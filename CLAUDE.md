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

22. **【V3.6】無編號短條文藥物被當「無內容」**
    - 症狀:9.6、9.8、9.13、9.15、9.16.2、9.23、9.33、9.40、9.5.2 等 9 個藥物展開後沒內容
    - 原因:這些藥物的條文是直接寫在藥名行之後,沒有 1./2./3. 編號 (例如 9.6 「限惡性腫瘤患者患有惡性腹水...」)
    - parser 只認編號條文 → 整段被忽略
    - 做法:parser 改成「先找第一個編號條文 1.」,有就從這開始; 沒有就把藥名行之後當單一條文 (標 `_is_unnumbered`)
    - 結果:從 10 個無內容降到 0 個

23. **【V3.6】胰臟神經內分泌瘤等癌別衝突**
    - 症狀:9.31 Sunitinib「胰臟神經內分泌瘤」被同時歸類為「肝膽胰胃癌」+「其他癌」(切片外溢)
    - 原因:keyword 「胰臟」「胰腺」會優先匹配「肝膽胰胃癌」,但臨床上應該歸 NET (其他癌)
    - 做法:加排除規則 — 條文前 50 字含「神經內分泌」「間質腫瘤」「GIST」時,跳過「肝膽胰胃癌」「大腸直腸癌」分類
    - 同樣處理:腸胃道間質瘤 (GIST) 不該歸大腸或胃癌

24. **【V3.6】父項目 cancers 沒包含子項目所有 cancers**
    - 症狀:9.5 Paclitaxel 父項目 cancers=[乳/肺/婦/其他],但 9.5.2 子項目是肝膽胰胃癌 → 父項目切片外溢到肝膽胰胃癌
    - 原因:父項目 cancers 從原始解析 (繼承父表面文字),沒包含子的擴充
    - 做法:後處理階段 — 父項目的 cancers 加上所有子項目 cancers 的 union
    - 結果:外溢從 3 個降到 0 個

25. **【V3.6】Header 警示「有新版」機制**
    - 需求:當 GitHub Actions 偵測到健保署有新版時,前端要顯示警示
    - 做法:JS unlock 後呼叫 GitHub API
      `GET /repos/{owner}/{repo}/issues?labels=nhi-update&state=open`
      有未關閉的 nhi-update issue → 從 title 抓日期 → 跟 brand-data-date 比對 → 不一樣顯示橘色警示徽章
    - 從 location.hostname 推斷 GitHub repo (限 GitHub Pages 環境)
    - 失敗時靜默,不影響使用

26. **【V3.7】教學資料按鈕的事件冒泡問題**
    - 症狀:點教學資料按鈕反而觸發了藥物展開/收合
    - 原因:藥物 header 整塊綁了 click handler,按鈕在 header 內按下會冒泡
    - 做法:用事件委派(document level)+ stopPropagation() 阻止冒泡

27. **【V3.7】教學資料 JS 沒包 <script> 標籤**
    - 症狀:openEducation is not defined
    - 原因:程式插入 HTML 時忘了在新區塊外圍加 <script> 標籤,造成 JS 變成 HTML body 文字
    - 做法:確保插入位置前後是 </script> + <script> 配對,或自己包

28. **【V3.10】Header 加「最後檢查時間」確認爬蟲沒掛**
    - 需求:目前只有「有新版」才會跳通知,沒新版時 Sela 無法確認 workflow 是否還在跑
    - 做法:打 GitHub API `/actions/workflows/check-nhi-update.yml/runs?per_page=1` 抓最後一次 run 的 `created_at`
    - 顯示策略: 剛剛 / 今天 / 昨天 / N 天前 / 30 天以上顯示日期
    - 警示門檻:超過 14 天沒跑顯示橘色 (workflow 排程是每週一)
    - hover tooltip 補完整時間 + workflow 結果 (成功/失敗/⋯)
    - 順便把資料日期文字從「資料截止 115/4/23」改成「程式參考的資料是 115年4月23日」
    - 重點:`brand-data-date` 加 `data-date="115.4.23"` 屬性,讓 `checkUpdateNotice` 比對日期時讀屬性而非顯示文字 — 之後改顯示格式不會打到 regex

29. **【V3.11】PDF parser 漏抓的「歷史藥」直到健保署更新才被發現**
    - 症狀:做 115/5/22 更新差異報告時發現「新增」5 個藥(9.49/9.84/9.99/9.135/9.136),但其中 9.49 Abiraterone (條文最新日 114/6/1)、9.99 Gilteritinib (條文最新日 113/6/1)、9.84 Copanlisib (這次標"刪除")實際在 115/4/23 規定本來就有,是 V3.9 解析時就漏抓
    - 連帶:9.48 (Eribulin) 的 items / per_cancer["其他癌"] / search_text 都吃進了 9.49 整段內容; 9.98 (Pemigatinib) 的最後 item.header 吃進 9.99 字首
    - 原因:parser 沒設「下一個 9.X. 編號就是切點」這個邊界,造成漏抓的編號條文被合併到前一個藥
    - 做法:這次手工清理 — 把 9.48 items 從 7 個截回 2 個 (轉移性乳癌 + 脂肪肉瘤);per_cancer["其他癌"] / common_data / search_text 也都重建; 補加 9.49 / 9.99 / 9.135 / 9.136 完整條文;9.84 標 `deleted: true` 保留編號 (灰底淡出 + 紅色"已刪除 115/6/1"標籤,健保署也是用"(刪除)"寫法保留條文編號)
    - 教訓:下次重跑 parser 時應加上「9.X. 編號 + 英文藥名」邊界檢測,任一藥的條文若包含其他 9.X. 編號 = parser bug,該報錯而非靜默合併

30. **【V4.0.0 兩層 diff：法規更新有「編號層」+「條文層」兩個層級】**
    - 症狀：V3.11 跟進 115/5/22 更新時只比對「9.X 編號出現/消失」，漏掉 10 個既有編號的「內部條文修訂」，Sela 用 9.69 PD-L1 截圖才撞到 P016 術前輔助 nivolumab(115/6/1)完全缺漏
    - 原因：diff 方法論只做編號層，沒做條文層
    - 做法：建立兩層 diff 引擎(diff_engine.py)——(1)編號層比對新增/刪除；(2)條文層把每個 9.X 段落忽略空白後逐條比對，標出所有含 (115/6/1) 的新條文。實測除驗證 V3.11 的 10 個外，**多抓到 9.51 Regorafenib**(V3.11 名單外)、**排除 9.71 Venetoclax**(純 OCR 雜訊:R-CHOP 連字號被讀成控制字元 \\u0002)
    - 教訓：每次更新前一定先跑兩層 diff，產 DIFF 報告給 Sela 確認再重建。掃描全 PDF 找 `(11X/X/X)` 標記是抓條文層變動的關鍵

31. **【V4.0.0 search_text 沒跟著 items 重生 → 搜尋索引與顯示不同步】**
    - 症狀：寬驗證(逐藥比對 App vs PDF)發現 9.49/9.99/9.135/9.136/9.84 的 search_text 是 null;9.98 Pemigatinib 的 search_text 整段塞著 9.99 Gilteritinib 條文(items 在 V3.11 已清,search_text 沒清)
    - 原因：V3.11 手工改了 items 但沒重生 search_text。(註:有 runtime fallback `if(!d.search_text)` 從 items 補,所以 5 個 null 的其實搜得到;9.98 因非 null 不觸發 fallback,溢出是真的)
    - 做法：**全庫 149 個藥 search_text 一律從 items 重新產生**(format = `lower(name+brand+每個 item header+每個 subitem text)`,用 143/149 逐字回歸驗證格式正確);並把跨癌藥的 per_cancer 切片內容也納入 search_text,讓 P016/術前輔助等可被查到
    - 教訓：任何改 items/per_cancer 後,**一律重生 search_text**,別靠 runtime fallback

32. **【V4.0.0 前言適應症句被 parser 吃掉】**
    - 症狀：寬驗證發現 9.68 Radium-223(整句「限治去勢抗性攝護腺癌…」)、9.19 Estramustine(「限晚期前列腺癌…」)、9.56 Brentuximab(「限用於成人患者」)的「前言」不見了
    - 原因：條文在藥名行和第「1.」項之間的引言,V3.9 parser 只處理「完全無編號」(坑 #22)的情形,沒處理「有前言又有編號項」的混合情形,前言被丟棄
    - 做法：把前言補成第一個 `_is_unnumbered` item,放在編號項之前
    - 教訓：parser 要區分三種：純編號 / 純無編號 / 前言+編號混合

33. **【V4.1.1 篩選選項藏在摺疊線以下 = 等於沒有】**
    - 症狀：「只顯示需事前審查」開關放在篩選面板最後一節，手機上癌別(10 pills)+藥物類型把它擠到視窗外，使用者回報「要先勾別的才會出現」。
    - 原因：靠捲動才看得到的選項，在手機上等於隱形；且它是全域開關，不該排在兩大 pill 區之後。
    - 做法：把它移到面板最上面（癌別之前），開啟面板即見。
    - 教訓：手機面板上「全域開關/重要選項」要放在不需捲動就看得到的位置；別假設使用者會捲到底。

34. **【V4.1.2 flexbox 面板捲不動 = min-height:0 經典坑】**
    - 症狀：篩選面板下半（藥物類型下半 + 底部按鈕）看不到，電腦滑鼠滾輪也滾不動。
    - 原因：`.filter-panel` 是 `display:flex;flex-direction:column;overflow-y:auto` + 100vh；`.filter-body` 是 `flex:1` 但**沒有** `overflow-y` 也**沒有** `min-height:0`。flex 子項預設 `min-height:auto`（不會小於內容），於是 header+body+footer 剛好等於 100vh、面板永遠不溢出 → 不出捲軸；body 自己又沒開捲動 → 內容被裁、捲不動。
    - 做法：scroll 容器要落在 body：`.filter-body{overflow-y:auto;min-height:0;-webkit-overflow-scrolling:touch}`，面板改 `overflow:hidden`。(同一條 CSS 也修好「關於」面板。)
    - 教訓：**flex column 裡要捲動的子項，一定要 `min-height:0` + `overflow-y:auto`**；只在外層 flex 容器設 overflow 不會生效。V4.1.1 移位置只是遮掩症狀，沒治本。

## 四、發版同步清單 (Rule 1 補完)

每次發版必須同步改的位置 (這次 V3.10/V3.11 中間有 5 版斷檔的教訓):

1. `index.html` 行 ~1521 `<span class="brand-version">vX.Y</span>`
2. `index.html` 行 ~1526 `<span class="brand-data-date" data-date="115.X.Y" data-effective="115.X.Y">` 顯示文字
3. `CLAUDE.md`「踩過的坑」加新編號 (只加不刪)
4. `CLAUDE.md`「版本歷程」表加 row
5. `CLAUDE.md`「一句話總結」更新

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
| V3.10 | Header 加「最後檢查 N 天前」(GitHub Actions API);資料日期文字改為「程式參考的資料是 115年4月23日」+ data-date 屬性 |
| V3.11 | 跟進 115/5/22 公告 (6/1 生效):補回 9.49 Abiraterone / 9.99 Gilteritinib (V3.9 parser 漏抓的歷史藥);新增 9.135 Capivasertib / 9.136 Fruquitinib;9.84 Copanlisib 標"已刪除"(灰底淡出 + 紅色標籤);Header 改「115年5月22日公告，115年6月1日生效」|
| V3.12 | 「關於」面板的資料來源加上「前往健保署藥品給付規定下載最新版」連結 (https://www.nhi.gov.tw/ch/cp-7593-ad2a9-3397-1.html),方便 Sela 拿到下次更新 PDF |
| V4.0.0 | **兩層 diff 重做 115/6/1 更新**:13 個法規變動(9.69 術前輔助 nivolumab + P016 表格列、續用評估改 i-RECIST、9.3/9.4/9.5.1 給付架構重整、9.2/9.20/9.51/9.66/9.129/9.130 條文修訂、9.84 刪除日期更正為 113/6/1)。**寬驗證修 3 類既有 bug**:全庫 search_text 重生(含 per_cancer)、補回 9.68/9.19/9.56 前言。多抓到 9.51、排除假陽性 9.71 |
| V4.1.0 | **對齊 SELA Kit**（.gitignore / favicon 套件 / 根 README / SELA-handoff）。**新增前端功能**：每藥「複製連結」深連結、「常用清單」(localStorage 星號 + 只看常用)、「最近搜尋」chips、「副作用照護」跳轉癌症希望基金會、列印優化(@media print 只印展開的藥)。候選工作 #1 自動切片驗證(32 藥 0 可疑)、#2 自動下載機制審查一併交付。 |
| V4.1.1 | **修 bug**：「只顯示需事前審查」開關原本是篩選面板**最後一個** section，手機上落在摺疊線以下、要往下捲才看得到（使用者誤以為「勾了別的才出現」）。移到面板**最上面**（癌別之前），開啟即見。 |
| V4.1.2 | **修真正的根因**：篩選面板（與「關於」面板共用 CSS）根本捲不動——`.filter-body` 是 `flex:1` 但沒 `overflow-y`/`min-height:0`，flex 子項剛好填滿面板、內容被裁掉且不出捲軸（電腦滑鼠也滾不動）。修法：`.filter-body` 加 `overflow-y:auto; min-height:0`，面板改 `overflow:hidden`。V4.1.1 把 事審 移上來只是讓它看得到，沒解決捲動。 |
| V4.1.3 | **UI 整理**：篩選 pill 從 `flex-wrap`（變寬度→參差不齊）改成**固定 2 欄 grid**（等寬對齊），名稱靠左、數量靠右（`margin-left:auto`），圓角由 100px 收成 10px 的整齊 chip。解決面板「凌亂」感。 |
| V4.1.4 | **修 pill 數字出框**：5 字長癌名（大腸直腸癌/血液淋巴癌/肝膽胰胃癌）把數字擠出框外。名稱改包 `.pill-name`(`flex:1;min-width:0;overflow:hidden;ellipsis`)、數字 `flex-shrink:0`，數字永遠留在框內。 |
| V4.1.5 | **pill 改上下兩層**：名稱在上（整顆寬度、不再截斷長癌名）、數字置中在下。dot/名稱包 `.pill-main`，數字獨立一行；隱藏 check（active 已用填色表示）。 |

> **版號規則變更（V4.0.0 起）：** 本專案自 V4.0.0 改採 SELA Kit 嚴格三位版號 `V<a>.<b>.<c>`（每位 0–9、逢十進位）。V3.0–V3.12 為 Kit 前舊編碼，依「保留歷史 + 從下版開始嚴格」保留不動；本次為功能版，因 V3.x 早已超過 .9，依逢十進位由 b 進位至 a，落點 V4.0.0（屬進位、非破壞性大改版）。

> 註:V3.5–V3.9 的版本歷程未記錄於本表,改動內容散見「踩過的坑 #19–#27」。

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

V4.1.0 已完成：#3 複製連結、#4 列印優化、#5 常用清單、#6 最近搜尋、#8 副作用照護(ecancer 跳轉)。
#1 自動切片驗證、#2 自動下載機制審查 已產出報告（32 藥 0 可疑；自動下載閉環仍待實機驗證，步驟見報告）。

**仍未做：**

1. **品質指標附件整合** — 國民健康署「癌症診療核心測量指標」強制申報 **60 項**（13 癌別、59 頁掃描檔已有乾淨 OCR）。份量大且屬「品質申報指標」領域，跟「藥物速查」不同；**待 Sela 決定放這個 SPA / 獨立工具 / 併入 CCM Manual** 再做。
2. **ecancer 直連深連結（強化版）** — 目前「副作用照護」按鈕跳到 ecancer 用藥資料庫首頁讓使用者自行搜尋。若要直接深連結到該藥頁面(`drug.ecancer.org.tw/<id>`)，需先取得 ecancer 全藥索引建學名→ID 對應表（其僅覆蓋 5 癌、整體約 64% 命中）。
3. **自動下載 PDF 機制實機驗證** — 程式邏輯已審查無誤，待在 GitHub Actions 上手動觸發驗證閉環（步驟見 V4.1.0 驗證報告）。

---

## 九、一句話總結

V3.4.2 完成了「**健保署有更新 → 自動下載 PDF → 寄 Email 通知 Sela → 點連結下載 PDF → 給 Claude 重做 → 推送**」的閉環自動化。V3.10 補上「最後檢查 N 天前」讓沒新版時也能確認爬蟲還活著。V3.11 完整跑過第一次健保更新流程 (115/4/23 → 115/5/22),意外撿回 V3.9 parser 漏抓的 2 個歷史藥。V3.12 加上健保署下載頁連結,讓 Sela 找下次更新 PDF 不用再 Google。下版重點仍是 parser 邊界檢測 (避免條文溢出合併)。

V4.0.0 把 115/6/1 更新用「兩層 diff」重做一遍 (編號層 + 條文層),抓回 V3.11 漏的 10+1 個內部條文修訂(含 9.69 術前輔助 nivolumab/P016);並用「寬驗證」逐藥比對 App vs PDF,順手修掉 V3.9/V3.11 留下的 3 類 bug(search_text 沒重生、9.98 溢出、9.68/9.19/9.56 前言遺失)。從此「兩層 diff + 寬驗證 + search_text 一律重生」成為每次更新的標準流程。

V4.1.0 對齊 SELA Kit（首次），並補上一批個管師日常會用到的前端小功能（複製連結、常用、最近搜尋、副作用照護跳轉、列印優化）。剩下最大一塊是 60 項品質指標附件，因屬不同領域待定放哪再做。
