#!/usr/bin/env python3
"""從 data/*.json 產生全站靜態頁面（首頁、29 區、各里）與 sitemap，讓搜尋引擎收錄。

用法：python3 scripts/build-pages.py   （Python 3.8+，無外部套件）
資料由 scripts/fetch-data.mjs 產生；GitHub Actions 每月抓完資料後會跑這支。
"""
import json
import os
import shutil
from collections import Counter
from html import escape
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://ntpc-trash-countdown.sectools.tw"
NAME = "新北垃圾車倒數"
UTM = "utm_source=ntpc-trash&utm_medium=referral&utm_campaign=crosslink"
SECTOOLS = f"https://sectools.tw/?{UTM}"
SECTOOLS_TOOLS = f"https://sectools.tw/tools?{UTM}"
GITHUB = "https://github.com/stwater20/ntpc-trash-countdown"
ADSENSE = "ca-pub-1946121873919285"
OFFICIAL = "https://crd-rubbish.epd.ntpc.gov.tw/"
NOTICE = "https://crd-rubbish.epd.ntpc.gov.tw/dispPageBox/Ntpcepd/NtpIndex.aspx?ddsPageID=EPDNEWS"
DATASET = "https://data.ntpc.gov.tw/datasets/edc3ad26-8ae7-4916-a00b-bc6048d19bf8"
WD = "日一二三四五六"
ASSET_V = "3"
UPDATED = ""

RELATED = [
    ("🚛", "台北垃圾車倒數", "台北市版本：清運點倒數＋每週時刻表＋日曆提醒", "https://tpe-trash-countdown.sectools.tw/"),
    ("🌀", "颱風假機率計算器", "依停班停課門檻與歷史數據，估算明天放不放颱風假", "https://typhoon.sectools.tw/"),
    ("🏝️", "台灣連假倒數", "下一個連假還有幾天？附請最少假、休最長假攻略", "https://taiwan-holiday-countdown.sectools.tw/"),
    ("⛽", "台灣油價預測", "依中油浮動油價機制試算下週汽柴油漲跌", "https://oil-price.sectools.tw/"),
    ("🚕", "計程車跳表估算", "用手機 GPS 邊搭邊跳表，內建各縣市費率", "https://taxi.sectools.tw/"),
    ("🔐", "密碼外洩查詢", "檢查密碼是否曾外洩、測試強度並產生強密碼", "https://password.sectools.tw/"),
]


def e(s):
    return escape(str(s), quote=True)


def path_of(*parts):
    return "/" + "".join(quote(p) + "/" for p in parts)


def url_of(*parts):
    return SITE + path_of(*parts)


def utm(u):
    return u + ("&" if "?" in u else "?") + UTM


def days_text(flags):
    d = [WD[i] for i, f in enumerate(flags) if f == "1"]
    return "週" + "、".join(d) if d else "—"


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>"


ICON = {
    "pin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.6"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    "cal": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></svg>',
    "loc": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/><circle cx="12" cy="12" r="7"/></svg>',
}
SHARE = """<div class="share-row" aria-label="分享本站">
  <button type="button" class="share-btn" data-share="facebook" aria-label="分享到 Facebook" title="Facebook"><svg viewBox="0 0 24 24"><path d="M22 12a10 10 0 1 0-11.6 9.9v-7H7.9V12h2.5V9.8c0-2.5 1.5-3.9 3.8-3.9 1.1 0 2.2.2 2.2.2v2.5h-1.3c-1.2 0-1.6.8-1.6 1.6V12h2.8l-.4 2.9h-2.4v7A10 10 0 0 0 22 12Z"/></svg></button>
  <button type="button" class="share-btn" data-share="line" aria-label="分享到 LINE" title="LINE"><svg viewBox="0 0 24 24"><path d="M12 3C6.5 3 2 6.6 2 11c0 3.9 3.5 7.2 8.3 7.9.3.1.8.2.9.5.1.3.1.7 0 1l-.1.9c0 .3-.2 1 .9.5s6-3.5 8.2-6.1c1.5-1.6 2.2-3.3 2.2-4.8C22.4 6.6 17.9 3 12 3Zm-3.6 10.4H6.4c-.3 0-.5-.2-.5-.5V8.9c0-.3.2-.5.5-.5s.5.2.5.5v3.5h1.5c.3 0 .5.2.5.5s-.2.5-.5.5Zm2-.5c0 .3-.2.5-.5.5s-.5-.2-.5-.5V8.9c0-.3.2-.5.5-.5s.5.2.5.5v4Zm4.8 0c0 .2-.1.4-.3.5h-.2c-.2 0-.3-.1-.4-.2l-2-2.8v2.5c0 .3-.2.5-.5.5s-.5-.2-.5-.5V8.9c0-.2.1-.4.3-.5h.2c.2 0 .3.1.4.2l2 2.8V8.9c0-.3.2-.5.5-.5s.5.2.5.5v4Zm3.3-2.5c.3 0 .5.2.5.5s-.2.5-.5.5h-1.5v1h1.5c.3 0 .5.2.5.5s-.2.5-.5.5h-2c-.3 0-.5-.2-.5-.5V8.9c0-.3.2-.5.5-.5h2c.3 0 .5.2.5.5s-.2.5-.5.5h-1.5v1h1.5Z"/></svg></button>
  <button type="button" class="share-btn" data-share="threads" aria-label="分享到 Threads" title="Threads"><svg viewBox="0 0 24 24"><path d="M17.3 11.1c-.1 0-.2-.1-.3-.1-.2-3-1.8-4.7-4.6-4.7h-.1c-1.6 0-3 .7-3.9 2l1.5 1c.6-.9 1.6-1.1 2.4-1.1 1 0 1.7.3 2.2.8.3.4.6 1 .7 1.7-.8-.1-1.6-.2-2.5-.1-2.5.1-4.1 1.6-4 3.6.1 1 .6 1.9 1.4 2.4.7.5 1.6.7 2.6.6 1.2-.1 2.2-.5 2.9-1.4.5-.7.9-1.5 1-2.6.6.4 1 .8 1.3 1.4.5 1 .5 2.7-.9 4.1-1.2 1.2-2.7 1.8-4.9 1.8-2.4 0-4.3-.8-5.5-2.3C5.5 16.8 4.9 14.7 4.9 12c0-2.7.6-4.8 1.8-6.3C7.9 4.2 9.8 3.4 12.2 3.4c2.4 0 4.3.8 5.6 2.3.6.8 1.1 1.7 1.4 2.7l1.7-.5c-.4-1.3-1-2.4-1.8-3.4C17.5 2.6 15.2 1.6 12.2 1.6 9.2 1.6 6.9 2.6 5.3 4.6 3.9 6.4 3.1 8.9 3.1 12c0 3.1.8 5.6 2.2 7.4 1.6 2 3.9 3 6.9 3 2.6 0 4.5-.7 6-2.2 2-2 2-4.5 1.3-6.1-.4-1.2-1.3-2.2-2.2-3Zm-4.7 4.6c-1 .1-2.1-.4-2.2-1.4 0-.7.5-1.6 2.3-1.7h.6c.7 0 1.3.1 1.8.2-.2 2.5-1.4 2.9-2.5 2.9Z"/></svg></button>
  <button type="button" class="share-btn" data-share="x" aria-label="分享到 X" title="X"><svg viewBox="0 0 24 24"><path d="M17.8 3h3.1l-6.8 7.7 8 10.6h-6.3l-4.9-6.4L5.3 21.3H2.2l7.3-8.3L1.8 3h6.4l4.4 5.9L17.8 3Zm-1.1 16.4h1.7L7.4 4.8H5.6l11.1 14.6Z"/></svg></button>
  <button type="button" class="share-btn" data-share="copy" aria-label="複製連結" title="複製連結"><svg viewBox="0 0 24 24"><path d="M10.6 13.4a1 1 0 0 1 0-1.4l3.5-3.5a3 3 0 0 1 4.2 4.2l-2.1 2.1a1 1 0 1 1-1.4-1.4l2.1-2.1a1 1 0 0 0-1.4-1.4L12 13.4a1 1 0 0 1-1.4 0Zm2.8-2.8a1 1 0 0 1 0 1.4l-3.5 3.5a3 3 0 0 1-4.2-4.2l2.1-2.1a1 1 0 1 1 1.4 1.4L7.1 12.7a1 1 0 0 0 1.4 1.4L12 10.6a1 1 0 0 1 1.4 0Z"/></svg></button>
</div>"""


def head(title, desc, canonical, jsonld=(), robots="index,follow,max-image-preview:large"):
    return f"""<!DOCTYPE html>
<html lang="zh-Hant-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{e(canonical)}">
<meta name="theme-color" content="#0a8f5f" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0d131c" media="(prefers-color-scheme: dark)">
<meta name="author" content="Sectools.tw">
<meta name="application-name" content="{NAME}">
<meta name="apple-mobile-web-app-title" content="垃圾車倒數">
<meta name="format-detection" content="telephone=no">
<link rel="icon" href="/assets/icon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="manifest" href="/manifest.webmanifest">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{NAME}｜Sectools.tw">
<meta property="og:locale" content="zh_TW">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{SITE}/assets/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="新北市垃圾車時間查詢：即時倒數＋日曆提醒">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{SITE}/assets/og-image.png">
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="stylesheet" href="/assets/app.css?v={ASSET_V}">
<script>try{{var t=localStorage.getItem("theme");if(t==="dark"||t==="light")document.documentElement.dataset.theme=t}}catch(e){{}}</script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE}" crossorigin="anonymous"></script>
{"".join(ld(j) for j in jsonld)}
</head>"""


def header():
    return f"""<a class="sr-only" href="#tool">跳到查詢工具</a>
<header class="site-header">
  <div class="container">
    <a class="brand" href="/" aria-label="{NAME} 首頁"><img src="/assets/icon.svg" alt="" width="32" height="32"><span>{NAME}<small>新北市垃圾車時間查詢</small></span></a>
    <nav class="nav" aria-label="主選單">
      <a href="/#tool">查詢</a>
      <a href="/#districts">各區時間表</a>
      <a href="/#faq">常見問題</a>
      <a class="ext" href="{SECTOOLS_TOOLS}" target="_blank" rel="noopener">更多工具 ↗</a>
    </nav>
    <button type="button" class="icon-btn" id="themeBtn" aria-label="切換深淺色"></button>
  </div>
</header>"""


def tool(title="找你家的垃圾車"):
    return f"""<section class="app" id="tool" aria-label="垃圾車時間查詢">
  <div>
    <div class="card favs" id="favs" hidden><h2>⭐ 我的常用清運點</h2><div class="chips" id="favList"></div></div>
    <div class="card finder">
      <h2><span class="step">1</span>{e(title)}</h2>
      <button type="button" class="btn btn-primary btn-block" id="geoBtn" style="margin-top:14px">{ICON['loc']}找我附近的清運點</button>
      <div class="or">或手動選擇</div>
      <div class="row2">
        <div class="field"><label for="city">行政區</label><select id="city"><option>載入中⋯</option></select></div>
        <div class="field"><label for="village">里別</label><select id="village" disabled><option>先選行政區</option></select></div>
      </div>
      <div class="field"><label for="q">搜尋路名、地標或路線</label><input type="search" id="q" placeholder="例如：中山路、公園、A14" disabled autocomplete="off" enterkeyhint="search"></div>
      <div class="stops" id="stops" aria-live="polite"></div>
    </div>
    <div class="notice"><span>⚠️</span><span>颱風、春節等可能停收，出門前看 <a href="{NOTICE}" target="_blank" rel="noopener">環保局公告</a>。</span></div>
  </div>
  <div id="detail"></div>
</section>"""


def promo():
    return f"""<section class="section"><div class="container">
  <a class="promo" href="{SECTOOLS}" target="_blank" rel="noopener">
    <span class="promo-icon" aria-hidden="true">🧰</span>
    <span class="promo-text"><b>本站由 Sectools.tw 製作與維護</b><span>Sectools.tw 還有颱風假計算、連假倒數、油價預測等更多免費實用小工具，歡迎來逛逛</span></span>
    <span class="promo-cta">前往 Sectools.tw →</span>
  </a>
  <h2 class="title" style="margin-top:34px">你可能也會用到</h2>
  <p class="sub">同樣由 Sectools.tw 製作的免費工具</p>
  <div class="related">{"".join(f'<a href="{e(utm(u))}" target="_blank" rel="noopener"><span class="e" aria-hidden="true">{em}</span><span><b>{e(n)}</b><span>{e(d)}</span></span></a>' for em, n, d, u in RELATED)}</div>
</div></section>"""


def footer(cities):
    top = cities[:12]
    return f"""<footer class="site-footer">
  <div class="container">
    <div class="cols">
      <div>
        <a class="brand" href="/"><img src="/assets/icon.svg" alt="" width="32" height="32"><span>{NAME}</span></a>
        <p style="margin-top:10px">免費查詢新北市 29 區垃圾車、資源回收、廚餘的收運時間，即時倒數並一鍵加入手機日曆提醒。資料來自 <a href="{DATASET}" target="_blank" rel="noopener">新北市資料開放平臺</a>，每月自動更新。</p>
        <p style="margin-top:8px">本站由 <a href="{SECTOOLS}" target="_blank" rel="noopener"><b>Sectools.tw</b></a> 製作與維護，非新北市政府官方網站。</p>
        {SHARE}
      </div>
      <div>
        <h3>熱門行政區</h3>
        <ul>{"".join(f'<li><a href="{path_of(c["name"])}">{e(c["name"])}垃圾車時間</a></li>' for c in top[:6])}</ul>
        <ul>{"".join(f'<li><a href="{path_of(c["name"])}">{e(c["name"])}垃圾車時間</a></li>' for c in top[6:12])}</ul>
      </div>
      <div>
        <h3>相關連結</h3>
        <ul>
          <li><a href="{SECTOOLS}" target="_blank" rel="noopener">Sectools.tw 首頁</a></li>
          <li><a href="{SECTOOLS_TOOLS}" target="_blank" rel="noopener">Sectools.tw 更多免費工具</a></li>
          <li><a href="{utm('https://tpe-trash-countdown.sectools.tw/')}" target="_blank" rel="noopener">台北垃圾車倒數</a></li>
          <li><a href="{OFFICIAL}" target="_blank" rel="noopener">新北市環保局清運查詢</a></li>
          <li><a href="/privacy.html">隱私權政策</a></li>
          <li><a href="{GITHUB}" target="_blank" rel="noopener">GitHub 原始碼</a></li>
        </ul>
      </div>
    </div>
    <div class="copy"><span>© 2026 <a href="{SECTOOLS}" target="_blank" rel="noopener">Sectools.tw</a>・資料更新：{UPDATED}</span><span>表定時間僅供參考，實際以現場為準。</span></div>
  </div>
</footer>
<script src="/assets/app.js?v={ASSET_V}" defer></script>
</body>
</html>
"""


def body(attrs=""):
    return f"<body{attrs}>"


def faq_html(items):
    return '<div class="faq">' + "".join(
        f'<details><summary>{e(q)}</summary><div class="a">{a}</div></details>' for q, a in items) + "</div>"


def faq_ld(items):
    import re
    strip = lambda s: re.sub(r"<[^>]+>", "", s)
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": strip(a)}} for q, a in items]}


def crumbs_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


def crumbs_html(items):
    out = []
    for i, (n, u) in enumerate(items):
        out.append(e(n) if i == len(items) - 1 else f'<a href="{e(u.replace(SITE, "") or "/")}">{e(n)}</a>')
    return '<nav class="crumbs" aria-label="麵包屑">' + "<span>/</span>".join(out) + "</nav>"


def district_grid(cities, hl=None):
    return '<div class="districts">' + "".join(
        f'<a href="{path_of(c["name"])}"{" aria-current=page" if c["name"] == hl else ""}>{e(c["name"])}<span>{c["n"]:,} 點</span></a>' for c in cities) + "</div>"


PUBLISHER = {"@type": "Organization", "name": "Sectools.tw", "url": "https://sectools.tw/",
             "logo": "https://sectools.tw/wp-content/uploads/2024/10/cropped-logo-192x192.jpg"}


def time_range(stops):
    ts = sorted((s[2] for s in stops), key=lambda t: t.zfill(5))
    return ts[0], ts[-1]


def peak_hour(stops):
    h = Counter(int(s[2].split(":")[0]) for s in stops).most_common(1)[0][0]
    return f"{h}:00–{h + 1}:00"


def write(rel, html):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------- pages
def build_home(idx, cities, updated):
    total = idx["total"]
    desc = f"新北市垃圾車幾點來？免費查詢板橋、新莊、中和、永和、三重等 29 區 {total:,} 個清運點的垃圾車、資源回收、廚餘時間，即時倒數下一班、GPS 找最近清運點，一鍵加入手機日曆提醒。每月自動更新。"
    title = "新北市垃圾車時間查詢｜垃圾車幾點到？即時倒數＋日曆提醒"
    faq = [
        ("新北市垃圾車幾點來？怎麼查？",
         f"在上方選擇行政區與里別（或按「找我附近的清運點」用 GPS 定位），點選你家附近的清運點，就會顯示表定時間與「下一班還有多久」的倒數。全市 {total:,} 個清運點都查得到。"),
        ("新北市星期三、星期日有收垃圾嗎？",
         f"沒有。依新北市開放資料，全市 {total:,} 個清運點中只有極少數（不到 0.1%）在週三、週日收運，絕大多數是<strong>週三、週日停收</strong>，一般垃圾、資源回收、廚餘都一樣。每個清運點的收運星期可在每週時刻表中看到。"),
        ("可以設定垃圾車提醒嗎？要裝 App 嗎？",
         "不用裝 App。選好清運點後按「加入手機日曆提醒」，會下載一個 .ics 日曆檔，打開即可加入 iPhone、Android 或 Google 日曆，每週自動重複，並在垃圾車到之前 10 分鐘通知你。"),
        ("垃圾車時間準嗎？會提早或延後嗎？",
         "本站顯示的是新北市環保局公告的表定時間。實際抵達時間會受交通、天候影響，通常前後數分鐘，建議提前到點等候。颱風、春節等特殊情況請以環保局公告為準。"),
        ("資源回收和廚餘是同一台車嗎？",
         "新北市採「垃圾不落地」，一般垃圾車後方通常會跟著資源回收車，廚餘則掛在垃圾車或回收車上。本站把垃圾、回收、廚餘的收運星期分開顯示，方便你確認當天能丟什麼。"),
        ("資料多久更新一次？來源是哪裡？",
         f"資料來自<a href=\"{DATASET}\" target=\"_blank\" rel=\"noopener\">新北市資料開放平臺「新北市垃圾車路線」</a>（新北市政府環境保護局），每月 1 號自動抓取最新資料，目前資料日期為 {updated}。"),
        ("可以把清運點分享給家人嗎？",
         "可以。選好清運點後按「分享」，網址會記住這個清運點，家人打開連結就直接看到同一個倒數與時刻表。也可以按「收藏」把家裡、公司等多個清運點存起來一鍵切換。"),
    ]
    jsonld = [
        {"@context": "https://schema.org", "@type": "WebApplication", "name": "新北市垃圾車時間查詢", "alternateName": NAME,
         "url": SITE + "/", "description": desc, "applicationCategory": "UtilityApplication", "operatingSystem": "Any",
         "inLanguage": "zh-Hant-TW", "isAccessibleForFree": True, "image": SITE + "/assets/og-image.png",
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "TWD"}, "publisher": PUBLISHER,
         "isPartOf": {"@type": "WebSite", "name": "Sectools.tw", "url": "https://sectools.tw/"}},
        {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE + "/", "inLanguage": "zh-Hant-TW", "publisher": PUBLISHER},
        faq_ld(faq),
    ]
    html = head(title, desc, SITE + "/", jsonld) + body() + header() + f"""
<main>
<div class="container">
  <section class="hero">
    <span class="eyebrow"><i></i>{e(updated)} 更新・新北市 29 區全收錄</span>
    <h1>新北市垃圾車<em>幾點到？</em><br>即時倒數，再也不追車</h1>
    <p class="lead">選你家附近的清運點，馬上知道下一班垃圾車還有多久，一鍵加進手機日曆，每週提前 10 分鐘提醒你。</p>
    <div class="stats">
      <span class="stat"><b>{total:,}</b>個清運點</span>
      <span class="stat"><b>29</b>個行政區</span>
      <span class="stat"><b>免費</b>免下載 App</span>
      <span class="stat"><b>每月</b>自動更新</span>
    </div>
  </section>
  {tool()}
</div>

<section class="section"><div class="container">
  <h2 class="title">三步搞定垃圾車時間</h2>
  <p class="sub">比翻里長公告、比官方地圖更快</p>
  <div class="steps">
    <div class="card"><span class="ico">{ICON['pin']}</span><h3>選清運點</h3><p>用行政區＋里別瀏覽、輸入路名搜尋，或用 GPS 直接找離你最近的 20 個清運點。</p></div>
    <div class="card"><span class="ico">{ICON['clock']}</span><h3>看倒數</h3><p>直接告訴你「下一班還有幾分幾秒」，垃圾、回收、廚餘分開算，再也不用自己換算星期。</p></div>
    <div class="card"><span class="ico">{ICON['cal']}</span><h3>加日曆提醒</h3><p>一鍵產生每週重複的日曆事件，提前 10 分鐘通知，iPhone、Android、Google 日曆都能用。</p></div>
  </div>
</div></section>

<section class="section" id="districts"><div class="container">
  <h2 class="title">新北市各區垃圾車時間表</h2>
  <p class="sub">點進行政區，查看各里清運點、路線與完整收運時刻</p>
  {district_grid(cities)}
</div></section>

<section class="section"><div class="container narrow">
  <h2 class="title">為什麼用這個工具？</h2>
  <p class="sub">我們實測了官方查詢網，把最常卡住的地方都改掉了</p>
  <div class="table-wrap"><table class="compare">
    <thead><tr><th>一般查詢方式</th><th>新北垃圾車倒數</th></tr></thead>
    <tbody>
      <tr><td>進站先跳全螢幕公告，每次都要手動關</td><td>打開就是查詢工具，三步看到結果</td></tr>
      <tr><td>地圖載入慢、手機吃流量</td><td>輕量清單介面，秒開省流量</td></tr>
      <tr><td>只列「星期＋時段」，要自己換算下一班</td><td>直接倒數下一班還有多久</td></tr>
      <tr><td>沒有提醒功能</td><td>一鍵加入手機日曆，每週提前提醒</td></tr>
      <tr><td>查詢結果無法分享、不能收藏</td><td>可分享網址、可收藏多個清運點</td></tr>
    </tbody>
  </table></div>
</div></section>

<section class="section" id="faq"><div class="container narrow">
  <h2 class="title">常見問題</h2>
  {faq_html(faq)}
</div></section>
</main>
{promo()}
""" + footer(cities)
    write("index.html", html)


def build_district(city, stops, cities, updated):
    villages = {}
    for s in stops:
        villages.setdefault(s[1], []).append(s)
    lines = {s[8] for s in stops}
    t0, t1 = time_range(stops)
    peak = peak_hour(stops)
    n = len(stops)
    title = f"{city}垃圾車時間查詢｜{len(villages)} 里清運點路線、時刻表＋即時倒數"
    desc = f"{city}垃圾車幾點到？收錄{city} {len(villages)} 個里、{n:,} 個清運點、{len(lines)} 條路線的垃圾車與資源回收時間（{t0}–{t1}），即時倒數下一班、GPS 找最近清運點，一鍵加入手機日曆提醒。"
    canon = url_of(city)
    crumbs = [("首頁", SITE + "/"), (f"{city}垃圾車時間", canon)]
    top_v = sorted(villages.items(), key=lambda kv: -len(kv[1]))[:3]
    faq = [
        (f"{city}垃圾車幾點來？",
         f"{city}的垃圾車表定收運時間從 {t0} 到 {t1}，以 {peak} 這個時段的清運點最多。每個清運點時間不同，請在上方選擇你家的里別與清運點查看精確時間與倒數。"),
        (f"{city}星期三、星期日有收垃圾嗎？",
         f"{city}和新北市其他行政區一樣，絕大多數清運點<strong>週三、週日停收</strong>。各清運點的垃圾、資源回收、廚餘收運星期，可以在每週時刻表中確認。"),
        (f"{city}有幾個垃圾車清運點？",
         f"依新北市開放資料（{updated}），{city}共有 {n:,} 個清運點、{len(lines)} 條收運路線，分布在 {len(villages)} 個里；清運點最多的是"
         + "、".join(f"{e(v)}（{len(l)} 點）" for v, l in top_v) + "。"),
        (f"怎麼設定{city}垃圾車提醒？",
         "選好清運點後按「加入手機日曆提醒」，下載 .ics 檔並打開，即可加入 iPhone、Android 或 Google 日曆，每週自動重複、提前 10 分鐘通知。"),
    ]
    jsonld = [crumbs_ld(crumbs), faq_ld(faq)]
    vlinks = "".join(f'<a href="{path_of(city, v)}">{e(v)}<span style="color:var(--muted);font-size:.74rem"> {len(l)}</span></a>' for v, l in villages.items())
    html = head(title, desc, canon, jsonld) + body(f' data-city="{e(city)}"') + header() + f"""
<main>
<div class="container">
  <section class="hero">
    {crumbs_html(crumbs)}
    <h1>{e(city)}垃圾車時間查詢</h1>
    <p class="lead">{e(city)} {len(villages)} 個里、{n:,} 個清運點的垃圾車、資源回收與廚餘時間，選好清運點立刻倒數下一班，還能加進手機日曆提醒。</p>
    <div class="stats">
      <span class="stat"><b>{n:,}</b>個清運點</span>
      <span class="stat"><b>{len(villages)}</b>個里</span>
      <span class="stat"><b>{len(lines)}</b>條路線</span>
      <span class="stat"><b>{e(t0)}–{e(t1)}</b>收運時段</span>
    </div>
  </section>
  {tool(f"找{city}的垃圾車")}
</div>

<section class="section"><div class="container">
  <h2 class="title">{e(city)}各里垃圾車時間表</h2>
  <p class="sub">點選里名，查看該里所有清運點的完整收運時刻與路線</p>
  <div class="vlist">{vlinks}</div>
</div></section>

<section class="section"><div class="container narrow">
  <h2 class="title">{e(city)}垃圾車常見問題</h2>
  {faq_html(faq)}
</div></section>

<section class="section"><div class="container">
  <h2 class="title">其他行政區</h2>
  {district_grid(cities, city)}
</div></section>
</main>
{promo()}
""" + footer(cities)
    write(f"{city}/index.html", html)
    return villages


def build_village(city, village, stops, siblings, cities, updated):
    stops = sorted(stops, key=lambda s: (s[2].zfill(5), s[0]))
    lines = sorted({s[8] for s in stops})
    t0, t1 = time_range(stops)
    n = len(stops)
    gdays = Counter(i for s in stops for i, f in enumerate(s[5]) if f == "1")
    common = "、".join(WD[i] for i in range(7) if gdays[i] > 0) or "—"
    sample = "、".join(dict.fromkeys(s[0] for s in stops))
    sample = sample[:60] + ("⋯" if len(sample) > 60 else "")
    title = f"{city}{village}垃圾車時間表｜{n} 個清運點幾點到＋即時倒數"
    desc = f"{city}{village}垃圾車幾點來？{n} 個清運點（{sample}）的垃圾車、資源回收、廚餘收運時間 {t0}–{t1}，含路線與每週收運日，可即時倒數並加入手機日曆提醒。"
    canon = url_of(city, village)
    crumbs = [("首頁", SITE + "/"), (f"{city}", url_of(city)), (f"{village}垃圾車時間", canon)]
    faq = [
        (f"{city}{village}垃圾車幾點到？",
         f"{village}共有 {n} 個清運點，表定時間從 {t0} 到 {t1}。完整清單請見下方時刻表，點任一清運點即可看到「下一班還有多久」的倒數。"),
        (f"{village}哪幾天收垃圾？",
         f"{village}的清運點收運日為週{common}（各清運點不完全相同），週三、週日通常停收。資源回收與廚餘收運日請看時刻表中的各欄。"),
    ]
    jsonld = [crumbs_ld(crumbs), faq_ld(faq)]

    def row(s):
        key = f"{city}~{village}~{s[0]}|{s[2]}|{s[8]}"
        return (f'<tr><td class="tm">{e(s[2])}</td><td><a href="#{e(quote(key))}">{e(s[0])}</a></td>'
                f'<td class="days">{days_text(s[5])}</td><td class="days">{days_text(s[6])}</td>'
                f'<td class="days">{days_text(s[7])}</td><td>{e(s[8])}</td></tr>')

    sib = "".join(f'<a href="{path_of(city, v)}">{e(v)}</a>' for v in siblings if v != village)
    html = head(title, desc, canon, jsonld) + body(f' data-city="{e(city)}" data-village="{e(village)}"') + header() + f"""
<main>
<div class="container">
  <section class="hero">
    {crumbs_html(crumbs)}
    <h1>{e(city)}{e(village)}垃圾車時間表</h1>
    <p class="lead">{e(village)} {n} 個清運點的垃圾車、資源回收與廚餘時間（{e(t0)}–{e(t1)}），點清運點即時倒數下一班，一鍵加入手機日曆提醒。</p>
    <div class="stats">
      <span class="stat"><b>{n}</b>個清運點</span>
      <span class="stat"><b>{len(lines)}</b>條路線</span>
      <span class="stat"><b>{e(t0)}–{e(t1)}</b>收運時段</span>
    </div>
  </section>
  {tool(f"{village}的垃圾車倒數")}
</div>

<section class="section"><div class="container">
  <h2 class="title">{e(city)}{e(village)}清運點與收運時間</h2>
  <p class="sub">依表定時間排序・資料日期 {e(updated)}・點清運點名稱可即時倒數</p>
  <div class="table-wrap"><table class="sched">
    <thead><tr><th>表定時間</th><th>清運點</th><th>🗑️ 一般垃圾</th><th>♻️ 資源回收</th><th>🥬 廚餘</th><th>路線</th></tr></thead>
    <tbody>{"".join(row(s) for s in stops)}</tbody>
  </table></div>
</div></section>

<section class="section"><div class="container narrow">
  <h2 class="title">{e(village)}垃圾車常見問題</h2>
  {faq_html(faq)}
</div></section>

<section class="section"><div class="container">
  <h2 class="title">{e(city)}其他里</h2>
  <div class="vlist">{sib}</div>
  <p style="margin-top:14px"><a href="{path_of(city)}">← 回到{e(city)}垃圾車時間</a></p>
</div></section>
</main>
{promo()}
""" + footer(cities)
    write(f"{city}/{village}/index.html", html)


def build_static(cities):
    privacy = head("隱私權政策｜" + NAME, f"{NAME}的隱私權政策：說明本站如何使用瀏覽器儲存、定位與第三方廣告服務。", SITE + "/privacy.html") + body() + header() + f"""
<main class="container narrow prose-page">
  <h1>隱私權政策</h1>
  <p>{NAME}（以下稱「本站」）由 <a href="{SECTOOLS}" target="_blank" rel="noopener">Sectools.tw</a> 製作與維護。我們重視你的隱私，本站不需要註冊、不收集姓名、電話等個人資料。</p>
  <h2>瀏覽器本機儲存</h2>
  <p>你選擇的清運點、收藏清單與深淺色設定只存在你自己瀏覽器的 localStorage，不會傳到我們的伺服器。清除瀏覽器資料即可刪除。</p>
  <h2>定位資訊</h2>
  <p>只有在你按下「找我附近的清運點」並同意授權時，瀏覽器才會提供位置。位置只在你的裝置上用來計算最近的清運點，不會上傳或保存。</p>
  <h2>日曆檔案</h2>
  <p>「加入手機日曆提醒」產生的 .ics 檔在你的瀏覽器中即時生成，不經過任何伺服器。</p>
  <h2>第三方服務與廣告</h2>
  <ul>
    <li>本站使用 Google AdSense 顯示廣告。Google 等第三方供應商會使用 Cookie，依據使用者先前造訪本站或其他網站的紀錄放送廣告。</li>
    <li>你可以前往 <a href="https://adssettings.google.com/" target="_blank" rel="noopener">Google 廣告設定</a> 停用個人化廣告，或至 <a href="https://www.aboutads.info/" target="_blank" rel="noopener">aboutads.info</a> 停用第三方供應商的 Cookie。</li>
    <li>網站託管於 GitHub Pages，GitHub 可能為安全與營運目的記錄存取紀錄（如 IP 位址）。</li>
  </ul>
  <h2>資料來源與免責聲明</h2>
  <p>垃圾車資料來自<a href="{DATASET}" target="_blank" rel="noopener">新北市資料開放平臺</a>，依政府資料開放授權條款使用。本站非新北市政府官方網站，表定時間僅供參考，實際以現場及<a href="{OFFICIAL}" target="_blank" rel="noopener">新北市環保局</a>公告為準。</p>
  <h2>聯絡我們</h2>
  <p>有任何問題或建議，歡迎到 <a href="{GITHUB}/issues" target="_blank" rel="noopener">GitHub Issues</a> 或 <a href="https://sectools.tw/about?{UTM}" target="_blank" rel="noopener">Sectools.tw 關於我們</a> 聯繫。</p>
</main>
{promo()}
""" + footer(cities)
    write("privacy.html", privacy)

    nf = head("找不到頁面｜" + NAME, "找不到這個頁面，回到新北市垃圾車時間查詢首頁。", SITE + "/404.html", robots="noindex") + body() + header() + f"""
<main class="container narrow prose-page" style="text-align:center">
  <img src="/assets/icon.svg" alt="" width="84" height="84" style="margin:20px auto">
  <h1>垃圾車開走了⋯⋯</h1>
  <p>找不到這個頁面，可能網址打錯或資料已更新。</p>
  <p style="margin-top:18px"><a class="btn btn-primary" href="/">回到首頁查垃圾車時間</a></p>
  <h2 style="margin-top:36px">直接選行政區</h2>
  {district_grid(cities)}
</main>
""" + footer(cities)
    write("404.html", nf)


def main():
    idx = json.loads((ROOT / "data/index.json").read_text(encoding="utf-8"))
    cities = idx["cities"]
    updated = idx["updated"]
    global UPDATED
    UPDATED = updated

    # 清掉上一輪產生的分區頁（行政區、里名可能變動）
    for c in ROOT.iterdir():
        if c.is_dir() and c.name.endswith("區") and (c / "index.html").exists():
            shutil.rmtree(c)

    urls = [(SITE + "/", "1.0", "weekly")]
    geo = []
    build_home(idx, cities, updated)
    for c in cities:
        name = c["name"]
        stops = json.loads((ROOT / f"data/{name}.json").read_text(encoding="utf-8"))["stops"]
        geo.append({"name": name,
                    "lon": round(sum(s[3] for s in stops) / len(stops), 5),
                    "lat": round(sum(s[4] for s in stops) / len(stops), 5)})
        villages = build_district(name, stops, cities, updated)
        urls.append((url_of(name), "0.9", "monthly"))
        for v, vs in villages.items():
            build_village(name, v, vs, list(villages), cities, updated)
            urls.append((url_of(name, v), "0.7", "monthly"))
    build_static(cities)
    urls.append((SITE + "/privacy.html", "0.2", "yearly"))

    (ROOT / "data/geo.json").write_text(json.dumps(geo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, pr, cf in urls:
        sm.append(f"  <url><loc>{escape(u)}</loc><lastmod>{updated}</lastmod><changefreq>{cf}</changefreq><priority>{pr}</priority></url>")
    sm.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
    print(f"OK: {len(urls)} pages, sitemap written")


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
