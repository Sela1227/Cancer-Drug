#!/usr/bin/env python3
"""
健保署第九節抗癌瘤藥物更新檢測

策略（依序嘗試直到成功）：
1. 主頁面: https://www.nhi.gov.tw/ch/cp-7593-ad2a9-3397-1.html
2. 已知 PDF 直連 (chap9_1150423.pdf)
3. RSS feed (如有)

成功後：
- 從網頁中找「第九節 抗癌瘤藥物(YY.M.D更新)」或「chap9_YYYMMDD」格式
- 比對 CURRENT_DATA_DATE
- 寫到 GITHUB_OUTPUT
"""
import os
import re
import sys
import time
import urllib.request
import urllib.error

# === 系統當前資料版本 (民國年.月.日) ===
# 每次重新從健保署抓 PDF 重建資料時，要更新這裡
CURRENT_DATA_DATE = "115.4.23"

TARGET_URL = "https://www.nhi.gov.tw/ch/cp-7593-ad2a9-3397-1.html"

# 多個 User-Agent
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Googlebot/2.1 (+http://www.google.com/bot.html)",  # Google 爬蟲，常被允許
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}

def fetch_page(url, ua, timeout=20):
    headers = dict(DEFAULT_HEADERS)
    headers["User-Agent"] = ua
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="replace")

def extract_chap9_date(html):
    """從 HTML 抓第九節抗癌瘤藥物的更新日期"""
    patterns = [
        # 主 pattern
        (r'第九節[\s　]*抗癌瘤藥物[\s　]*\(([\d.]+)更新\)', "標題日期"),
        (r'抗癌瘤藥物[^(\n]{0,30}\(([\d.]+)更新\)', "模糊匹配"),
        # PDF 檔名: chap9_1150423.pdf
        (r'chap9_(\d{7,8})', "PDF 檔名"),
    ]
    for pattern, name in patterns:
        m = re.search(pattern, html)
        if m:
            v = m.group(1)
            if re.match(r'^\d{7,8}$', v):
                # YYYMMDD 格式: 1150423 -> 115.4.23
                if len(v) == 7:
                    yy, mm, dd = v[:3], v[3:5], v[5:7]
                    v = f"{yy}.{int(mm)}.{int(dd)}"
                else:
                    yy, mm, dd = v[:4], v[4:6], v[6:8]
                    v = f"{int(yy[1:])}.{int(mm)}.{int(dd)}"
            print(f"    ({name}) 找到: {v}")
            return v
    return None

def normalize_date(d):
    """115.4.23 / 115.04.23 / 1150423 統一格式"""
    if not d:
        return None
    parts = re.split(r'[./]', d)
    if len(parts) == 3:
        return f"{int(parts[0])}.{int(parts[1])}.{int(parts[2])}"
    return d

def main():
    print(f"系統當前資料版本: {CURRENT_DATA_DATE}")
    print(f"目標頁面: {TARGET_URL}\n")
    
    new_date = None
    last_error = None
    
    for i, ua in enumerate(USER_AGENTS):
        ua_short = ua[:50] + "..." if len(ua) > 50 else ua
        print(f"嘗試 #{i+1}: {ua_short}")
        try:
            html = fetch_page(TARGET_URL, ua)
            print(f"  HTTP 200, HTML {len(html):,} bytes")
            new_date = extract_chap9_date(html)
            if new_date:
                break
            else:
                print(f"  解析失敗 (網頁結構變動?)")
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code}: {e.reason}")
            last_error = f"HTTP {e.code}"
        except Exception as e:
            print(f"  錯誤: {type(e).__name__}: {e}")
            last_error = str(e)
        
        # 不同 UA 之間加點延遲
        if i < len(USER_AGENTS) - 1:
            time.sleep(2)
    
    if not new_date:
        print(f"\n❌ 所有嘗試失敗。最後錯誤: {last_error}")
        # 寫個 output 讓 workflow 知道是失敗 (而非「無更新」)
        output_file = os.environ.get("GITHUB_OUTPUT")
        if output_file:
            with open(output_file, "a") as f:
                f.write(f"updated=false\n")
                f.write(f"check_failed=true\n")
                f.write(f"error={last_error or 'unknown'}\n")
        sys.exit(1)
    
    new_n = normalize_date(new_date)
    cur_n = normalize_date(CURRENT_DATA_DATE)
    
    print(f"\n比對結果:")
    print(f"  系統版本: {cur_n}")
    print(f"  網站版本: {new_n}")
    
    is_updated = new_n != cur_n
    
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"updated={'true' if is_updated else 'false'}\n")
            f.write(f"new_date={new_n}\n")
            f.write(f"old_date={cur_n}\n")
            f.write(f"check_failed=false\n")
    
    if is_updated:
        print(f"\n✅ 偵測到更新! {cur_n} → {new_n}")
    else:
        print(f"\n✓ 沒有更新 (皆為 {cur_n})")

if __name__ == "__main__":
    main()
