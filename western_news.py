"""西方权威免费数据源：Yahoo Finance官方新闻、Google News RSS、SEC EDGAR官方监管披露。
全部零新依赖（yfinance已在用；Google News/SEC用stdlib urllib+xml解析）。
"""
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd
import streamlit as st

_UA = {"User-Agent": "personal-quant-research-tool contact@example.com"}

FORM_LABELS = {
    "4": "Form 4·内部人交易", "8-K": "8-K·重大事件公告", "10-Q": "10-Q·季报",
    "10-K": "10-K·年报", "SC 13G": "13G·大股东持股", "SC 13G/A": "13G/A·大股东持股变更",
    "DEF 14A": "股东大会委托书", "S-8": "员工股票计划", "3": "Form 3·首次内部人登记",
    "6-K": "6-K·外国发行人报告", "20-F": "20-F·外国发行人年报",
}


@st.cache_data(ttl=900, show_spinner="拉取 Yahoo Finance 新闻…")
def yf_news(symbol, limit=10):
    import yfinance as yf
    items = yf.Ticker(symbol).news or []
    rows = []
    for it in items[:limit]:
        c = it.get("content", it) if isinstance(it, dict) else {}
        provider = c.get("provider")
        rows.append({
            "标题": c.get("title", ""),
            "摘要": c.get("summary") or c.get("description") or "",
            "时间": c.get("pubDate") or c.get("displayTime") or "",
            "来源": provider.get("displayName", "Yahoo Finance") if isinstance(provider, dict) else "Yahoo Finance",
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=900, show_spinner="拉取 Google News…")
def google_news(query, limit=15):
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers=_UA)
    xml_bytes = urllib.request.urlopen(req, timeout=10).read()
    root = ET.fromstring(xml_bytes)
    rows = []
    for item in root.findall(".//item")[:limit]:
        rows.append({
            "标题": item.findtext("title") or "",
            "来源": item.findtext("source") or "",
            "时间": item.findtext("pubDate") or "",
            "链接": item.findtext("link") or "",
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=21600, show_spinner=False)
def _cik_map():
    req = urllib.request.Request("https://www.sec.gov/files/company_tickers.json", headers=_UA)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


@st.cache_data(ttl=3600, show_spinner="读取 SEC EDGAR 官方数据…")
def sec_filings(symbol, limit=10):
    data = _cik_map()
    match = next((v for v in data.values() if v["ticker"].upper() == symbol.upper()), None)
    if not match:
        return pd.DataFrame()
    cik = str(match["cik_str"]).zfill(10)
    req = urllib.request.Request(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=_UA)
    sub = json.loads(urllib.request.urlopen(req, timeout=10).read())
    recent = sub["filings"]["recent"]
    n = min(limit, len(recent.get("form", [])))
    rows = []
    for i in range(n):
        form = recent["form"][i]
        acc = recent["accessionNumber"][i].replace("-", "")
        doc = recent["primaryDocument"][i]
        rows.append({
            "类型": FORM_LABELS.get(form, form),
            "日期": recent["filingDate"][i],
            "链接": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}",
        })
    return pd.DataFrame(rows)
