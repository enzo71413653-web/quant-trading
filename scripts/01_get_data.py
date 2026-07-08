"""01 · 取数：用 akshare 拉 A股/ETF 日线，存到 data/。
学习点：数据是一切的起点。先能稳定拿到数据，才谈策略。
用法：python scripts/01_get_data.py
"""
from pathlib import Path
import pandas as pd
import akshare as ak

DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)

# 改成你关心的标的（6 位代码）。示例 = 沪深300ETF(510300)
SYMBOL = "510300"
START, END = "20190101", "20261231"

# ETF 用 fund_etf_hist_em；个股改用 ak.stock_zh_a_hist(symbol="600519", ...)
df = ak.fund_etf_hist_em(symbol=SYMBOL, period="daily",
                         start_date=START, end_date=END, adjust="qfq")

# akshare 返回中文列名，统一改成回测/分析要用的英文
df = df.rename(columns={"日期": "Date", "开盘": "Open", "收盘": "Close",
                        "最高": "High", "最低": "Low", "成交量": "Volume"})
df["Date"] = pd.to_datetime(df["Date"])
df = df.set_index("Date").sort_index()

out = DATA / f"{SYMBOL}.csv"
df.to_csv(out, encoding="utf-8-sig")
print(f"[OK] 存到 {out}，共 {len(df)} 行")
print(df.tail(3)[["Open", "Close", "High", "Low", "Volume"]])
