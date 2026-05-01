#!/usr/bin/env python3
"""
健保署第九節抗癌瘤藥物更新檢測 + 自動下載 PDF

策略：
1. 多重備援抓取網頁，找出更新日期
2. 比對 CURRENT_DATA_DATE
3. 若有更新，找出 PDF 下載連結並下載到 artifact
4. 寫入 GITHUB_OUTPUT 讓 workflow 後續步驟接手
"""
import os
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

CURRENT_DATA_DATE = "115.4.23"
TARGET_URL = "https://www.nhi.gov.tw/ch/cp-7593-ad2a9-3397-1.html"

STRATEGIES = [
    {"name": "直連 (Chrome)", "url": TARGET_URL,
     "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
    {"name": "直連 (Safari)", "url": TARGET_URL,
     "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"},
    {"name": "r.jina.ai 代理", "url": f"https://r.jina.ai/{TARGET_URL}",
     "ua": "Mozilla/5.0"},
    {"name": "Google Cache", "url": f"https://webcache.googleusercontent.com/search?q=cache:{TARGET_URL}",
     "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
    {"name": "Wayback Machine", "url": f"https://web.archive.org/web/2024id_/{TARGET_URL}",
     "ua": "Mozilla/5.0"},
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
}

def fetch(url, ua, timeout=25, return_bytes=False):
    headers = dict(DEFAULT_HEADERS)
    headers["User-Agent"] = ua
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        if return_bytes:
            return raw
        return raw.decode("utf-8", errors="replace")

def extract_chap9_date(text):
    patterns = [
        (r'第九節[\s　]*抗癌瘤藥物[\s　]*\(([\d.]+)\s*更新\)', "標題日期"),
        (r'抗癌瘤藥物[^(\n]{0,30}\(([\d.]+)\s*更新\)', "模糊匹配"),
        (r'chap9_(\d{7,8})', "PDF 檔名"),
    ]
    for pattern, name in patterns:
        m = re.search(pattern, text)
        if m:
            v = m.group(1)
            if re.match(r'^\d{7,8}$', v):
                if len(v) == 7:
                    yy, mm, dd = v[:3], v[3:5], v[5:7]
                    v = f"{yy}.{int(mm)}.{int(dd)}"
                else:
                    yy, mm, dd = v[:4], v[4:6], v[6:8]
                    v = f"{int(yy[1:])}.{int(mm)}.{int(dd)}"
            print(f"    ({name}) 找到: {v}")
            return v
    return None

def extract_pdf_url(html, page_url):
    """從 HTML 中找第九節抗癌瘤藥物的 PDF 下載連結
    
    健保署的 HTML 結構大致為:
    第九節 抗癌瘤藥物(115.4.23更新) ... <a href="..chap9_1150423.pdf">pdf</a>
    或者:
    第九節 抗癌瘤藥物(115.4.23更新) ... <a href="/ch/dl-XXXXX-...pdf">pdf</a>
    """
    # 找第九節附近的內容
    idx = html.find("第九節")
    if idx < 0:
        return None
    # 抓第九節到下一個「第十節」之間的內容
    end_idx = html.find("第十節", idx)
    if end_idx < 0:
        end_idx = idx + 5000  # 如果找不到第十節，抓 5000 字
    section = html[idx:end_idx]
    
    # 找 PDF 連結
    # pattern 1: chap9_NNNNNNN.pdf
    m = re.search(r'href=["\']?([^"\'\s>]*chap9_\d+\.pdf[^"\'\s>]*)["\']?', section)
    if m:
        pdf_url = m.group(1)
    else:
        # pattern 2: dl-NNNNN-XXXXXXX-1.pdf 格式 (健保署 download URL)
        m = re.search(r'href=["\']?([^"\'\s>]*dl-\d+-[a-f0-9]+-\d+\.pdf[^"\'\s>]*)["\']?', section)
        if m:
            pdf_url = m.group(1)
        else:
            # pattern 3: 任何 .pdf
            m = re.search(r'href=["\']?([^"\'\s>]+\.pdf[^"\'\s>]*)["\']?', section)
            if m:
                pdf_url = m.group(1)
            else:
                return None
    
    # 把相對 URL 轉成絕對 URL
    if pdf_url.startswith('/'):
        pdf_url = "https://www.nhi.gov.tw" + pdf_url
    elif not pdf_url.startswith('http'):
        # 相對路徑，依 page_url 解析
        pdf_url = urllib.parse.urljoin(page_url, pdf_url)
    
    # 把 HTML entity 還原 (&amp; → &)
    pdf_url = pdf_url.replace('&amp;', '&')
    
    return pdf_url

def extract_pdf_url_from_markdown(md, page_url):
    """從 r.jina.ai 取得的 markdown 中找 PDF 連結
    
    markdown 格式: [text](url)
    """
    idx = md.find("第九節")
    if idx < 0:
        return None
    end_idx = md.find("第十節", idx)
    if end_idx < 0:
        end_idx = idx + 3000
    section = md[idx:end_idx]
    
    # markdown 連結: [name](url)
    m = re.search(r'\[([^\]]*chap9_\d+[^\]]*\.pdf)\]\(([^)]+)\)', section)
    if m:
        return m.group(2)
    m = re.search(r'\[([^\]]*\.pdf)\]\(([^)]+\.pdf[^)]*)\)', section)
    if m:
        return m.group(2)
    # 純 URL 也試試
    m = re.search(r'(https?://[^\s)]+chap9_\d+\.pdf)', section)
    if m:
        return m.group(1)
    return None

def normalize_date(d):
    if not d: return None
    parts = re.split(r'[./]', d)
    if len(parts) == 3:
        return f"{int(parts[0])}.{int(parts[1])}.{int(parts[2])}"
    return d

def main():
    print(f"系統當前資料版本: {CURRENT_DATA_DATE}")
    print(f"目標頁面: {TARGET_URL}\n")
    
    new_date = None
    pdf_url = None
    last_error = None
    success_strategy = None
    success_html = None
    
    for i, s in enumerate(STRATEGIES):
        print(f"嘗試 #{i+1}: {s['name']}")
        print(f"  URL: {s['url'][:80]}{'...' if len(s['url']) > 80 else ''}")
        try:
            html = fetch(s['url'], s['ua'])
            print(f"  HTTP 200, 內容 {len(html):,} bytes")
            new_date = extract_chap9_date(html)
            if new_date:
                success_strategy = s['name']
                success_html = html
                
                # 同時嘗試找 PDF URL
                if "r.jina.ai" in s['name']:
                    pdf_url = extract_pdf_url_from_markdown(html, TARGET_URL)
                else:
                    pdf_url = extract_pdf_url(html, TARGET_URL)
                if pdf_url:
                    print(f"    PDF URL: {pdf_url}")
                else:
                    print(f"    (未找到 PDF 下載連結)")
                break
            else:
                print(f"  解析失敗")
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code}: {e.reason}")
            last_error = f"{s['name']}: HTTP {e.code}"
        except Exception as e:
            print(f"  錯誤: {type(e).__name__}: {e}")
            last_error = f"{s['name']}: {e}"
        
        if i < len(STRATEGIES) - 1:
            time.sleep(2)
        print()
    
    if not new_date:
        print(f"\n❌ 所有策略都失敗")
        print(f"最後錯誤: {last_error}")
        output_file = os.environ.get("GITHUB_OUTPUT")
        if output_file:
            with open(output_file, "a") as f:
                f.write(f"updated=false\n")
                f.write(f"check_failed=true\n")
                f.write(f"error={last_error or 'unknown'}\n")
        sys.exit(1)
    
    new_n = normalize_date(new_date)
    cur_n = normalize_date(CURRENT_DATA_DATE)
    
    print(f"\n比對結果 (來源: {success_strategy}):")
    print(f"  系統版本: {cur_n}")
    print(f"  網站版本: {new_n}")
    
    is_updated = new_n != cur_n
    
    # === 如果有更新，下載 PDF ===
    pdf_downloaded = False
    pdf_path = None
    if is_updated and pdf_url:
        print(f"\n下載 PDF: {pdf_url}")
        try:
            # 先用相同 UA 嘗試
            pdf_bytes = fetch(pdf_url, STRATEGIES[0]['ua'], timeout=60, return_bytes=True)
            print(f"  PDF 大小: {len(pdf_bytes):,} bytes")
            # 存到 artifact 路徑
            os.makedirs("nhi_artifacts", exist_ok=True)
            pdf_filename = f"chap9_{new_n.replace('.', '_')}.pdf"
            pdf_path = f"nhi_artifacts/{pdf_filename}"
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            pdf_downloaded = True
            print(f"  ✅ 已存到 {pdf_path}")
        except Exception as e:
            print(f"  ❌ PDF 下載失敗: {e}")
            # 嘗試 r.jina.ai 代理 PDF (它也可以代理檔案)
            try:
                proxy_url = f"https://r.jina.ai/{pdf_url}"
                print(f"  改用代理: {proxy_url}")
                # 但 r.jina.ai 會把 PDF 轉 markdown，沒用
                # 直接放棄，讓人工下載
            except:
                pass
    
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"updated={'true' if is_updated else 'false'}\n")
            f.write(f"new_date={new_n}\n")
            f.write(f"old_date={cur_n}\n")
            f.write(f"check_failed=false\n")
            f.write(f"source={success_strategy}\n")
            f.write(f"pdf_url={pdf_url or ''}\n")
            f.write(f"pdf_downloaded={'true' if pdf_downloaded else 'false'}\n")
            if pdf_path:
                f.write(f"pdf_path={pdf_path}\n")
    
    if is_updated:
        print(f"\n✅ 偵測到更新! {cur_n} → {new_n}")
        if pdf_downloaded:
            print(f"   PDF 已下載: {pdf_path}")
        else:
            print(f"   PDF 自動下載失敗,需手動到健保署網站下載")
    else:
        print(f"\n✓ 沒有更新 (皆為 {cur_n})")

if __name__ == "__main__":
    main()
