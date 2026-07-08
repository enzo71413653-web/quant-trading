"""统一数据适配器：中/美/韩/日 行情 + 全球快讯。所有页面复用。
每次联网实时拉取；失败重试2次并回退本地 CSV 缓存。
"""
import re
import socket
import time
from pathlib import Path

import pandas as pd
import akshare as ak
import streamlit as st

# yfinance 的 curl 后端在含中文的路径下读不了 CA 证书(curl 77) → 复制到纯英文临时路径再指过去
try:
    import os
    import shutil
    import tempfile
    import certifi
    _src = certifi.where()
    if not _src.isascii():
        _dst = os.path.join(tempfile.gettempdir(), "claude_cacert.pem")
        if not os.path.exists(_dst):
            shutil.copy(_src, _dst)
        os.environ["CURL_CA_BUNDLE"] = _dst
        os.environ["SSL_CERT_FILE"] = _dst
        os.environ["REQUESTS_CA_BUNDLE"] = _dst
except Exception:
    pass

socket.setdefaulttimeout(20)
DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(exist_ok=True)


def _safe(name):
    return re.sub(r"[^0-9A-Za-z_.-]", "_", str(name))


def _norm_ak(df):
    df = df.rename(columns={"日期": "Date", "开盘": "Open", "收盘": "Close",
                            "最高": "High", "最低": "Low", "成交量": "Volume"})
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date").sort_index()[["Open", "High", "Low", "Close", "Volume"]]


def _from_yf(symbol, start, end):
    import yfinance as yf
    s, e = f"{start[:4]}-{start[4:6]}-{start[6:]}", f"{end[:4]}-{end[4:6]}-{end[6:]}"
    df = yf.Ticker(symbol).history(start=s, end=e, auto_adjust=True)
    if df is None or df.empty:
        raise ValueError("yfinance 空数据")
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "Date"
    return df[["Open", "High", "Low", "Close", "Volume"]]


def _from_ak_us(symbol, start, end):
    df = ak.stock_us_daily(symbol=symbol).reset_index()
    dcol = "date" if "date" in df.columns else df.columns[0]
    df = df.rename(columns={dcol: "Date", "open": "Open", "high": "High",
                            "low": "Low", "close": "Close", "volume": "Volume"})
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    s, e = f"{start[:4]}-{start[4:6]}-{start[6:]}", f"{end[:4]}-{end[4:6]}-{end[6:]}"
    return df.loc[s:e][["Open", "High", "Low", "Close", "Volume"]]


def _fetch(symbol, market, start, end):
    csv = DATA / f"{market}_{_safe(symbol)}.csv"
    last_err = None
    for _ in range(3):
        try:
            if market == "cn_stock":
                df = _norm_ak(ak.stock_zh_a_hist(symbol=symbol, period="daily",
                              start_date=start, end_date=end, adjust="qfq"))
            elif market == "cn_etf":
                df = _norm_ak(ak.fund_etf_hist_em(symbol=symbol, period="daily",
                              start_date=start, end_date=end, adjust="qfq"))
            elif market in ("us", "kr", "jp"):
                try:
                    df = _from_yf(symbol, start, end)
                except Exception:
                    if market == "us" and not symbol.startswith("^"):
                        df = _from_ak_us(symbol, start, end)
                    else:
                        raise
            else:
                raise ValueError(f"未知 market: {market}")
            if df is None or df.empty:
                raise ValueError("空数据")
            df.to_csv(csv, encoding="utf-8-sig")
            return df, "live"
        except Exception as e:
            last_err = e
            time.sleep(1.5)
    if csv.exists():
        return pd.read_csv(csv, index_col="Date", parse_dates=True), "cache"
    raise last_err


@st.cache_data(ttl=1800, show_spinner="联网拉取行情中…")
def get_price(symbol, market, start="20190101", end="20261231"):
    return _fetch(symbol, market, start, end)


def _fetch_news(keywords, limit):
    df = ak.stock_info_global_em()
    tcol = next((c for c in df.columns if "标题" in c or "title" in c.lower()), df.columns[0])
    scol = next((c for c in df.columns if "摘要" in c or "内容" in c or "简介" in c), None)
    dcol = next((c for c in df.columns if "时间" in c or "日期" in c or "date" in c.lower()), None)
    text = df[tcol].astype(str) + " " + (df[scol].astype(str) if scol else "")
    if keywords:
        pat = "|".join(re.escape(str(k)) for k in keywords if k)
        df = df[text.str.contains(pat, case=False, na=False)]
    out = pd.DataFrame({
        "时间": df[dcol].astype(str) if dcol else "",
        "标题": df[tcol].astype(str),
        "摘要": df[scol].astype(str) if scol else "",
    })
    return out.head(limit).reset_index(drop=True)


@st.cache_data(ttl=900, show_spinner="拉取快讯中…")
def get_news(keywords, limit=30):
    try:
        return _fetch_news(keywords, limit)
    except Exception:
        return pd.DataFrame(columns=["时间", "标题", "摘要"])
